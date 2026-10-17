"""Read Unicode cmap mappings from original TTF/OTF files; never modify fonts."""
from __future__ import annotations

from bisect import bisect_right
from functools import lru_cache
import struct


class FontCoverage:
    def __init__(self, data: bytes):
        if data[:4] not in (b"OTTO", b"\x00\x01\x00\x00", b"true"):
            raise ValueError("Expected a standalone TTF or OTF font")
        count = struct.unpack_from(">H", data, 4)[0]
        tables = {}
        for i in range(count):
            tag, _, offset, length = struct.unpack_from(">4sIII", data, 12 + i * 16)
            if offset + length > len(data):
                raise ValueError(f"Truncated font table: {tag!r}")
            tables[tag] = data[offset:offset + length]
        cmap = tables[b"cmap"]
        self.groups = []
        self.bmp = set()
        for i in range(struct.unpack_from(">H", cmap, 2)[0]):
            platform, encoding, offset = struct.unpack_from(">HHI", cmap, 4 + i * 8)
            if not (platform == 0 or (platform == 3 and encoding in (1, 10))):
                continue
            form = struct.unpack_from(">H", cmap, offset)[0]
            if form == 12:
                groups = [struct.unpack_from(">III", cmap, offset + 16 + j * 12)
                          for j in range(struct.unpack_from(">I", cmap, offset + 12)[0])]
                self.groups.append(([g[0] for g in groups], groups))
            elif form == 4:
                segments = struct.unpack_from(">H", cmap, offset + 6)[0] // 2
                starts = offset + 16 + 2 * segments
                deltas, ranges = starts + 2 * segments, starts + 4 * segments
                for j in range(segments):
                    start = struct.unpack_from(">H", cmap, starts + j * 2)[0]
                    end = struct.unpack_from(">H", cmap, offset + 14 + j * 2)[0]
                    delta = struct.unpack_from(">h", cmap, deltas + j * 2)[0]
                    displacement = struct.unpack_from(">H", cmap, ranges + j * 2)[0]
                    for cp in range(start, min(end, 65534) + 1):
                        if displacement:
                            glyph = struct.unpack_from(">H", cmap, ranges + j * 2 + displacement + 2 * (cp - start))[0]
                            if glyph:
                                glyph = (glyph + delta) & 65535
                        else:
                            glyph = (cp + delta) & 65535
                        if glyph:
                            self.bmp.add(cp)
        if not self.bmp and not self.groups:
            raise ValueError("Font has no supported Unicode cmap (4/12)")

    @lru_cache(maxsize=8192)
    def has(self, cp: int) -> bool:
        if cp in self.bmp:
            return True
        for starts, groups in self.groups:
            i = bisect_right(starts, cp) - 1
            if i >= 0:
                start, end, glyph = groups[i]
                if cp <= end and glyph + cp - start:
                    return True
        return False

    def missing(self, text: str) -> list[str]:
        return [c for c in dict.fromkeys(text) if c != "\n" and not self.has(ord(c))]
