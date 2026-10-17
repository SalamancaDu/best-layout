/* Internal raster compositor. No HTML/SVG output and no remote requests. */
async ({spec, images}) => {
  const canvas = document.createElement('canvas');
  canvas.width = spec.canvas.width;
  canvas.height = spec.canvas.height;
  const ctx = canvas.getContext('2d');
  if (!ctx) throw new Error('Canvas 2D is unavailable');
  if (!('letterSpacing' in ctx)) throw new Error('This Chromium lacks native Canvas letterSpacing; use a current Chromium');
  ctx.fillStyle = spec.canvas.background;
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  const imageReport = [];
  for (const g of spec.graphics) {
    if (g.type === 'rect') {
      ctx.fillStyle = g.color;
      ctx.fillRect(g.x, g.y, g.width, g.height);
    } else if (g.type === 'ellipse') {
      ctx.fillStyle = g.color;
      ctx.beginPath();
      ctx.ellipse(g.x + g.width / 2, g.y + g.height / 2, g.width / 2, g.height / 2, 0, 0, Math.PI * 2);
      ctx.fill();
    } else if (g.type === 'image') {
      const img = new Image();
      img.src = images[g.path];
      await img.decode();
      const scale = (g.fit === 'cover' ? Math.max : Math.min)(g.width / img.width, g.height / img.height);
      const w = img.width * scale, h = img.height * scale;
      const x = g.x + (g.width - w) * g.position[0], y = g.y + (g.height - h) * g.position[1];
      ctx.save();
      ctx.beginPath(); ctx.rect(g.x, g.y, g.width, g.height); ctx.clip();
      ctx.drawImage(img, x, y, w, h); ctx.restore();
      imageReport.push({path: g.path, original: [img.width, img.height], fit: g.fit});
    }
  }
  ctx.textBaseline = 'alphabetic';
  ctx.textAlign = 'left';
  ctx.direction = 'ltr';
  ctx.fontKerning = 'normal';
  const segmenter = new Intl.Segmenter('zh', {granularity: 'grapheme'});
  const opening = new Set(Array.from('（《〈「『【〔〖“‘([{'));
  const closing = new Set(Array.from('，。、；：？！）》〉」』】〕〗”’)]},.!?;:%％'));
  const word = c => /^[A-Za-z0-9@._:/%+\-—–]+$/u.test(c);
  const nonbreakingSpaces = new Set(['\u00A0', '\u202F']);
  const apostropheWord = /[A-Za-z]+(?:['’][A-Za-z]+)+/gu;
  const space = '[ \\u00A0\\u202F]*';
  const digits = '[0-9０-９]+';
  const numeral = `${digits}(?:[.,:，．：]${digits})*`;
  const prefix = `(?:[+＋\\-−－±$＄¥￥€£₩]${space}){0,2}`;
  const unit = '(?:KiB|MiB|GiB|KB|MB|GB|kg|km/h|km|cm|mm|px|°[ ]?[CF]|℃|℉|[%％‰‱°$＄¥￥€£₩₫]|' +
    '元|千克|公斤|千米|公里|厘米|毫米|小时|分钟|年月日|[年月日时分秒件人个米吨度])';
  const magnitude = '(?:万亿|千万|百万|十万|亿|万|千)';
  // Match complete units (e.g. 千克) before treating 千 as a magnitude.
  // Magnitudes can stand alone or qualify any supported unit, not only 元.
  const suffix = `(?:${unit}|${magnitude}(?:${space}${unit})?)`;
  const quantity = new RegExp(`${prefix}${numeral}(?:[-–—~～至]${prefix}${numeral})?(?:${space}${suffix})?`, 'gu');

  function protectedBreaks(text) {
    // UTF-16 offsets match RegExp indices and the grapheme offsets below.
    // A repeated ellipsis/dash can wrap between complete two-character pairs.
    const blocked = new Set();
    for (const pattern of [/…{2}|—{2}/gu, quantity, apostropheWord]) {
      for (const match of text.matchAll(pattern)) {
        for (let i = match.index + 1; i < match.index + match[0].length; i++) blocked.add(i);
      }
    }
    return blocked;
  }
  function measure(text, transform) {
    const metrics = ctx.measureText(text);
    const {scale_x: sx, scale_y: sy, skew_x: angle} = transform;
    // Positive angles lean the top of the glyph to the right. Shear is applied
    // after scaling, around each line's baseline, so multiline axes stay stable.
    const shear = -Math.tan(angle * Math.PI / 180) * sy;
    const xs = [];
    for (const x of [-metrics.actualBoundingBoxLeft, metrics.actualBoundingBoxRight]) {
      for (const y of [-metrics.actualBoundingBoxAscent, metrics.actualBoundingBoxDescent]) {
        xs.push(sx * x + shear * y);
      }
    }
    const ink = {left: Math.min(...xs), right: Math.max(...xs),
      top: -metrics.actualBoundingBoxAscent * sy, bottom: metrics.actualBoundingBoxDescent * sy};
    const left = Math.min(0, ink.left);
    const right = Math.max(metrics.width * sx, ink.right);
    return {ink, shear, left, width: right - left};
  }
  function legalBreak(a, b) {
    if (nonbreakingSpaces.has(a) || nonbreakingSpaces.has(b)) return false;
    if (opening.has(a) || closing.has(b)) return false;
    if (a === '—' && b === '—') return true; // Pair interiors are blocked separately.
    if (word(a) && word(b)) return false;
    return true;
  }
  function wrapParagraph(text, width, id, transform) {
    const chars = Array.from(segmenter.segment(text), v => v.segment);
    if (!chars.length) return [''];
    const blocked = protectedBreaks(text);
    const offsets = [0];
    for (const char of chars) offsets.push(offsets.at(-1) + char.length);
    const lines = [];
    let start = 0;
    while (start < chars.length) {
      let end = start, best = -1;
      while (end < chars.length) {
        const next = end + 1;
        const candidate = chars.slice(start, next).join('');
        if (measure(candidate, transform).width > width + 0.01) break;
        if (next === chars.length || (!blocked.has(offsets[next]) && legalBreak(chars[next - 1], chars[next]))) best = next;
        end = next;
      }
      if (best <= start) throw new Error(`${id}: word, number or punctuation group exceeds width; enlarge the box or reflow at the same readable size`);
      lines.push(chars.slice(start, best).join(''));
      start = best;
    }
    return lines;
  }
  const ink = [], blocks = [];
  for (const b of spec.blocks) {
    ctx.font = `${b.size}px "${b.font}"`;
    ctx.letterSpacing = `${b.letter_spacing}px`;
    ctx.fillStyle = b.color;
    const original = spec.copy[b.copy_id];
    const t = b.transform;
    const lines = b.lines || original.split('\n').flatMap(p => wrapParagraph(p, b.width, b.copy_id, t));
    if (lines.join('') !== original.replaceAll('\n', '')) throw new Error(`${b.copy_id}: line construction changed copy`);
    const row = {copy_id: b.copy_id, text: original, font: b.font, size: b.size, transform: t, lines: []};
    for (let i = 0; i < lines.length; i++) {
      const line = lines[i];
      const measured = measure(line, t);
      if (measured.width > b.width + 0.01) throw new Error(`${b.copy_id}: explicit line is too wide`);
      // Include natural and deliberately transformed overhangs in final pixels.
      let x = b.x - measured.left;
      if (b.align === 'center') x += (b.width - measured.width) / 2;
      if (b.align === 'right') x += b.width - measured.width;
      const baseline = b.y + (b.size + i * b.line_height) * t.scale_y;
      const r = {text: line, left: x + measured.ink.left, right: x + measured.ink.right,
        top: baseline + measured.ink.top, bottom: baseline + measured.ink.bottom,
        layout_left: x + measured.left, layout_right: x + measured.left + measured.width};
      if (r.left < b.x - 0.01 || r.right > b.x + b.width + 0.01 || r.top < b.y - 0.01 || r.bottom > b.y + b.height + 0.01) {
        throw new Error(`${b.copy_id}: glyph ink exceeds its text box: ${JSON.stringify(r)}; change layout, do not auto-shrink`);
      }
      if (r.right > r.left && r.bottom > r.top) {
        for (const other of ink) {
          if (Math.min(r.right, other.right) > Math.max(r.left, other.left) + 0.5 &&
              Math.min(r.bottom, other.bottom) > Math.max(r.top, other.top) + 0.5) {
            throw new Error(`${b.copy_id}: text overlaps ${other.copy_id}`);
          }
        }
        ink.push({...r, copy_id: b.copy_id});
      }
      if (t.scale_x === 1 && t.scale_y === 1 && t.skew_x === 0) {
        // Keep the established rasterization path for normal body text. Even
        // an equivalent translate() can change Chromium's fractional hinting.
        ctx.fillText(line, x, baseline);
      } else {
        ctx.save();
        ctx.transform(t.scale_x, 0, measured.shear, t.scale_y, x, baseline);
        ctx.fillText(line, 0, 0); // Explicit design transform; no hidden fitting.
        ctx.restore();
      }
      row.lines.push(r);
    }
    blocks.push(row);
  }
  const data = canvas.toDataURL('image/png').split(',')[1];
  if (!data) throw new Error('PNG encoding failed');
  return {data, blocks, images: imageReport, width: canvas.width, height: canvas.height};
}
