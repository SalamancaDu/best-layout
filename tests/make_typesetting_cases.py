"""Original test layouts; formal E/F/G copy is read from cases.md unchanged."""
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "tests/typesetting"


def block(key, font, x, y, width, height, size, color, **extra):
    return {"copy_id": key, "font": font, "x": x, "y": y, "width": width,
            "height": height, "size": size, "color": color, **extra}


def source(letter):
    body = (ROOT / "tests/cases.md").read_text(encoding="utf-8").split(f"## {letter}：", 1)[1].split("\n## ", 1)[0]
    return re.search(r"```text\n(.*?)\n```", body, re.S)[1].splitlines()[1:]


def save(name, width, height, background, copy, blocks, graphics=()):
    data = {"version": 1, "canvas": {"width": width, "height": height, "background": background},
            "copy": copy, "graphics": list(graphics), "blocks": blocks}
    (DEST / (name + ".json")).write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def font_sheet():
    fonts = json.loads((ROOT / "skills/best-layout/assets/fonts/manifest.json").read_text(encoding="utf-8"))["fonts"]
    data = {"version": 1, "canvas": {"width": 1800, "height": ((len(fonts) + 1) // 2) * 310 + 70,
                                    "background": "#F8F6EF"}, "copy": {}, "graphics": [], "blocks": []}
    for i, entry in enumerate(fonts):
        x, y = 70 + i % 2 * 880, 60 + i // 2 * 310
        label, sample = f"label{i}", f"sample{i}"
        data["copy"].update({label: entry["label"], sample: "山川有光"})
        for key, font, top, size in [(label, "source-han-sans", y, 28), (sample, entry["id"], y + 90, 96)]:
            data["blocks"].append(block(key, font, x, top, 780, 140, size, "#26372E"))
    return data


def main():
    DEST.mkdir(exist_ok=True)
    (DEST / "selected-fonts.json").write_text(json.dumps(font_sheet(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    wrap_copy = {"ellipsis": "观察日常……重新看见生活。", "temperature": "温度 20 ℃，湿度 50%。",
                 "prefix": "参考值 ± 3，价格 ￥ 128。"}
    save("line-breaks", 900, 450, "#F4F0E8", wrap_copy, [
        block("ellipsis", "source-han-sans", 40, 50, 220, 350, 40, "#252820"),
        block("temperature", "source-han-sans", 340, 50, 180, 350, 40, "#252820"),
        block("prefix", "source-han-sans", 580, 50, 280, 350, 40, "#252820"),
    ])
    e = dict(zip(["title", "tagline", "date", "time", "place", "admission"], source("E"), strict=True))
    save("concert", 1080, 1440, "#F26938", e, [
        block("title", "smiley", 80, 132, 920, 552, 218, "#252620", lines=["夜行", "音乐会"], line_height=260),
        block("tagline", "source-han-sans", 88, 772, 904, 74, 48, "#252620"),
        block("date", "wdxl", 88, 1040, 904, 116, 100, "#F5EEDF"),
        block("time", "source-han-sans", 88, 1180, 580, 62, 44, "#F5EEDF"),
        block("place", "source-han-sans", 88, 1295, 500, 64, 46, "#F5EEDF"),
        block("admission", "source-han-sans", 730, 1295, 262, 64, 46, "#F5EEDF", align="right"),
    ], [{"type": "rect", "x": 0, "y": 960, "width": 1080, "height": 480, "color": "#252620"},
        {"type": "rect", "x": 88, "y": 720, "width": 904, "height": 4, "color": "#252620"}])
    g = dict(zip(["title", "english", "subtitle", "date", "place", "time"], source("G"), strict=True))
    save("exhibition", 1080, 1440, "#982565", g, [
        block("title", "source-han-serif", 80, 175, 920, 510, 216, "#FFFFFF", lines=["看见", "声音"], line_height=248),
        block("english", "wdxl", 86, 755, 908, 104, 88, "#FF8A35"),
        block("subtitle", "source-han-sans", 86, 940, 908, 76, 54, "#FFFFFF"),
        block("date", "source-han-sans", 86, 1130, 908, 66, 42, "#982565"),
        block("place", "source-han-sans", 86, 1260, 580, 64, 46, "#982565"),
        block("time", "source-han-sans", 655, 1265, 339, 58, 40, "#982565", align="right"),
    ], [{"type": "rect", "x": 0, "y": 1080, "width": 1080, "height": 360, "color": "#FF8A35"},
        {"type": "rect", "x": 80, "y": 100, "width": 140, "height": 12, "color": "#FF8A35"}])
    f = {f"item{i:02}": line for i, line in enumerate(source("F"))}
    dense = [
        block("item00", "source-han-sans", 72, 50, 1008, 94, 76, "#234B40"),
        block("item01", "wdxl", 74, 157, 620, 58, 46, "#234B40"),
        block("item02", "source-han-sans", 72, 234, 330, 56, 40, "#242B26"),
        block("item03", "source-han-sans", 420, 234, 660, 56, 40, "#242B26"),
        block("item04", "source-han-sans", 72, 302, 1008, 60, 44, "#242B26"),
    ]
    # 20 approved copy items, five full paragraphs and three schedule rows.
    y = 410
    for title, paragraph in [(5, 6), (7, 8)]:
        dense += [block(f"item{title:02}", "source-han-sans", 72, y, 1008, 62, 48, "#234B40"),
                  block(f"item{paragraph:02}", "wenkai-gb", 72, y + 70, 1008, 166, 44, "#242B26", line_height=54)]
        y += 250
    dense.append(block("item09", "source-han-sans", 72, y, 1008, 62, 48, "#234B40"))
    for i in range(3):
        dense.append(block(f"item{10 + i:02}", "wenkai-gb", 72, y + 70 + 56 * i, 1008, 56, 44, "#242B26"))
    y += 260
    for title, paragraph in [(13, 14), (15, 16), (17, 18)]:
        dense += [block(f"item{title:02}", "source-han-sans", 72, y, 1008, 62, 48, "#234B40"),
                  block(f"item{paragraph:02}", "wenkai-gb", 72, y + 70, 1008, 166, 44, "#242B26", line_height=54)]
        y += 250
    dense.append(block("item19", "wenkai-gb", 72, 1955, 1008, 60, 42, "#234B40"))
    next(b for b in dense if b["copy_id"] == "item14")["lines"] = [
        "无需预约，按到场顺序登记。未成年人", "须由成年人陪同；每件物品先检查，", "再决定是否适合现场处理。"]
    save("dense", 1152, 2048, "#F5F3EC", f, dense,
         [{"type": "rect", "x": 72, "y": 382, "width": 1008, "height": 3, "color": "#234B40"}])
    title = "在日常之间，重新看见器物"
    long_copy = {"title": title, "body": "从杯、盘与花器出发，观察使用留下的痕迹。", "date": "2026.11.06—11.22", "place": "青禾空间"}
    save("long-portrait", 1080, 1440, "#EFE9DC", long_copy, [
        block("title", "xiangcui", 80, 200, 920, 500, 126, "#293A2F", lines=["在日常之间，", "重新看见器物"], line_height=176),
        block("body", "wenkai-gb", 80, 850, 920, 150, 48, "#293A2F", line_height=72,
              lines=["从杯、盘与花器出发，", "观察使用留下的痕迹。"]),
        block("date", "source-han-sans", 80, 1180, 920, 70, 46, "#293A2F"),
        block("place", "source-han-sans", 80, 1280, 920, 70, 46, "#293A2F"),
    ])
    save("long-wide", 1600, 900, "#EFE9DC", long_copy, [
        block("title", "xiangcui", 80, 140, 1440, 178, 106, "#293A2F"),
        block("body", "wenkai-gb", 80, 440, 1060, 145, 48, "#293A2F", line_height=72),
        block("date", "source-han-sans", 80, 730, 840, 70, 46, "#293A2F"),
        block("place", "source-han-sans", 1150, 730, 370, 70, 46, "#293A2F", align="right"),
    ])
    # After visual comparison, retain native proportions and a modest lean.
    # The earlier 1.4x width + 14-degree shear was rejected as too flat/wide.
    forward = {"title": "向前一步", "english": "RUN THE NIGHT", "tagline": "按自己的节奏出发",
               "date": "2026.11.07", "time": "19:30", "place": "环湖步道"}
    save("forward-poster", 1080, 1440, "#DAF07C", forward, [
        block("title", "source-han-sans", 82, 138, 916, 704, 300, "#24362C",
              lines=["向前", "一步"], line_height=326,
              transform={"skew_x": 6}),
        block("english", "wdxl", 82, 855, 916, 110, 83, "#24362C",
              transform={"skew_x": 6}),
        block("tagline", "source-han-sans", 82, 1010, 916, 66, 44, "#24362C"),
        block("date", "source-han-sans", 82, 1200, 560, 70, 48, "#DAF07C"),
        block("time", "source-han-sans", 700, 1200, 298, 70, 48, "#DAF07C", align="right"),
        block("place", "source-han-sans", 82, 1300, 916, 70, 48, "#DAF07C"),
    ], [{"type": "rect", "x": 0, "y": 1150, "width": 1080, "height": 290, "color": "#24362C"},
        {"type": "rect", "x": 82, "y": 102, "width": 916, "height": 8, "color": "#24362C"}])
    # Brief: a quiet exhibition with a tall editorial rhythm; no numeric style
    # instructions are supplied by the fictional user.
    light = {"title": "光的形状", "subtitle": "日常观察展", "body": "在明暗之间，停留片刻。",
             "date": "2026.11.06—11.22", "place": "青禾空间"}
    save("light-poster", 1080, 1440, "#F4EBDD", light, [
        block("title", "source-han-serif", 88, 110, 904, 770, 214, "#B33F2A",
              lines=["光的", "形状"], line_height=250,
              transform={"scale_x": 0.86, "scale_y": 1.55}),
        block("subtitle", "source-han-sans", 88, 930, 904, 70, 48, "#29352B"),
        block("body", "wenkai-gb", 88, 1045, 904, 70, 48, "#29352B"),
        block("date", "source-han-sans", 88, 1210, 904, 70, 44, "#29352B"),
        block("place", "source-han-sans", 88, 1310, 904, 70, 44, "#29352B"),
    ], [{"type": "rect", "x": 776, "y": 110, "width": 216, "height": 770, "color": "#B33F2A"}])


if __name__ == "__main__":
    main()
