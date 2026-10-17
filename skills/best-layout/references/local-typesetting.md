# 真实字体排字

代理决定内容与布局，再用脚本合成 PNG；用户不必写配置。程序使用 Chromium 原生字体塑形和 Canvas 栅格化，浏览器仅在内部运行，不生成 HTML 或 SVG 文件。

## 环境与调用

需要 Python 3.10+、Python Playwright 和支持 Canvas `letterSpacing` 的 Chromium。脚本不会自动安装依赖。实际测试环境为 Windows、Python 3.13、Playwright 1.57.0 和 Chromium，macOS／Linux 尚未实机验证。

```sh
python "<skill>/scripts/compose.py" --check-env
python "<skill>/scripts/compose.py" --list-fonts
python "<skill>/scripts/compose.py" "layout.json" "final.png"
```

将 `<skill>` 替换为当前技能位置。从任意目录运行均可。系统已有 Chrome／Edge 时加 `--channel chrome`／`--channel msedge`；其他已装 Chromium 用 `--chromium "实际可执行文件路径"`。不依赖个人字体目录。

缺环境时说明实际缺口，遵守宿主安装授权规则，不自动安装。用户自行准备环境可执行：

```sh
python -m pip install -r "<skill>/scripts/requirements.txt"
python -m playwright install chromium
```

已有可用浏览器则无需再下载。程序不联网渲染、不下载字体或调用图像服务，只加载本次选中的字库。

## 随附字体

原始字库、版权和许可证位于 [assets/fonts](../assets/fonts/)。具体来源、版本和 SHA-256 见 [manifest.json](../assets/fonts/manifest.json)。完整字体包约 103.5 MiB；复制整个技能文件夹即可携带，无需系统安装。字库文件未转换或修改；设计变换仅作用于排印到画布上的文字。

| font ID | 字库 | 注意 |
|---|---|---|
| `source-han-sans` | 思源黑体 CN **Bold** | 标题、导语、强对比信息；不是 Regular |
| `source-han-serif` | 思源宋体 CN **Heavy** | 展示标题；不作密集正文默认 |
| `wenkai-gb` | 霞鹜文楷 GB Regular | 人文正文，罕见字另核对 |
| `unbounded` | 标小智无界黑 | 强视觉标题 |
| `xiangcui` | 香萃等粗宋 | 标题或合适尺寸的短段落 |
| `qiji` | 齊伋體 | 古刻本字形；缺少不少标点、英文、数字 |
| `smiley` | 得意黑 Oblique | 已有原生倾斜，额外斜切时评估叠加效果 |
| `wdxl` | WD-XL 滑油字 SC Regular | 简体窄体展示字 |
| `marker` | 霞鹜漫黑 Regular | 手写感展示字 |
| `fusion-pixel` | 缝合像素字体 12px proportional zh_hans | 原尺寸优先用 12 的整数倍字号，缩小观看另核对 |

按角色选择少量字体，不把列表当作每图清单。首版携带上述 10 款；Oswald Stencil 因所选文件的分发证据未确认而排除。英文和数字可使用覆盖相应字符的现有字库，WD-XL 适合窄体展示，思源黑体 Bold 适合稳定的信息文字。代码与字体许可证相互独立，分发时保留各目录 OFL 与版权信息，见 [第三方许可说明](../THIRD_PARTY_NOTICES.md)。无需在成图中印版权注释。

## 配置

下面是 [随包提供的可执行最小例](../assets/examples/poster.json)，不是通用布局模板。可运行 `python "<skill>/scripts/compose.py" "<skill>/assets/examples/poster.json" "final.png"`。坐标和外框尺寸为最终像素；文字块 `x,y` 为外框左上角，首行基线为 `y + size * scale_y`，未变形时即 `y + size`。

```json
{
  "version": 1,
  "canvas": {"width": 1080, "height": 1440, "background": "#F4F0E8"},
  "copy": {"title": "山川有光", "date": "2026.10.16"},
  "graphics": [],
  "blocks": [
    {"copy_id": "title", "font": "source-han-serif", "x": 96, "y": 200,
     "width": 888, "height": 170, "size": 140, "color": "#252820"},
    {"copy_id": "date", "font": "source-han-sans", "x": 96, "y": 1200,
     "width": 888, "height": 60, "size": 42, "color": "#252820"}
  ]
}
```

`copy` 是 ID 到准确原文的映射；每个 ID 必须且只能被一个块引用。确需重复时为每次出现单独建 ID。可见文字只能来自这里，不另填易漂移的 `text` 字段。

文字块可选字段：

- `line_height`：基线距离，默认字号的 1.4 倍，不小于字号。
- `letter_spacing`：原生字距，默认 0；不逐字拉伸。
- `align`：`left`／`center`／`right`，默认左对齐。
- `lines`：用于语义分行的字符串数组；仅适用于没有换行的原文。各行直接连接必须逐字等于原文，包括空格。原文有 `\n` 时使用自动换行，保留段落。
- `transform`：设计用的整块字形变换，省略时保持原形。`scale_x` 控制拉宽／压窄、`scale_y` 控制拉高／压扁，默认均为 1；`skew_x` 为倾斜角度，默认 0，正数向右倾。代理根据主题自主选择，不要求用户填写参数。

例如标题采用 `"transform": {"scale_x": 1.1, "scale_y": 1.2, "skew_x": 12}`，表示比原排字横向放大 10%、纵向拉高 20%、向右倾斜 12°。这是说明参数含义的示例，不是固定推荐组合。缩放支持 0.05～20，倾斜角度支持 -85～85°；这些是运行数值边界，不是审美建议。

变换先缩放，再以各行基线为轴斜切；所有行使用同一组参数。字号和行距随 `scale_y` 变化，字形和字距随 `scale_x` 变化。`x,y,width,height` 始终表示最终画布中的外框，自动换行、对齐、越界及重叠检查都使用变换后的占位。给定 `lines` 可固定标题语义断行；放不下时调整版面，不会悄悄改变变换值。

文字直接从真实字库通过矩阵变换栅格化，不先生成低分辨率文字图再放大，也不修改字体原件。设计斜切不是新增的原生 Italic 款式。程序的边界检查不判断变形后的气质或字腔质量，仍须查看实际图片。

自动换行按实际字宽处理常见中文标点禁则，保护连续西文及词内撇号（如 `Don't`、`Don’t`）、数字、常见日期／时间，以及带空格的数字单位组合（如 `20 ℃`、`50 ‰`、`￥ 128`、`2 千克`、`10 万人`、`10 万件`）。不在不换行空格 U+00A0／U+202F 两侧自动断行，字库仍须覆盖原文字符。两字符省略号与破折号不从中间拆开；连续多组可以在完整两字符组之间换行。原有空格、字符与段落不被替换。整体放不下的词、数量或连接组会报错，需要重排。语义分行仍由代理核对；该算法不覆盖所有语言、单位及完整 CLReq 禁则。竖排、双向文本、行内多字体和变体选择符未实现，不以旋转、删除字符或回退冒充支持。

颜色使用不透明 `#RRGGBB`；画布背景另支持 `transparent`。`graphics` 里的几何与图片先绘制，文字最后绘制。支持下列对象（每行是独立示例，使用时加入数组）：

```json
{"type":"rect","x":80,"y":600,"width":920,"height":4,"color":"#D96343"}
{"type":"ellipse","x":800,"y":80,"width":180,"height":180,"color":"#D96343"}
{"type":"image","path":"assets/background.png","x":0,"y":0,"width":1080,"height":1440,"fit":"cover","position":[0.5,0.5]}
```

图片路径相对于配置文件，仅接受实际 PNG／JPEG／WebP。默认 `contain` 等比完整放入；`cover` 等比填满裁切。`position` 为 0～1 的横纵位置，默认居中。先检查素材，脚本不识别图片自带的字。

## 失败与检查

缺字报错包含文字块、字库、字符和 Unicode 码位，无系统字体回退。为整个块选择覆盖原文的合适字库，不删字、换标点或简繁转换；用户指定字体不可替换时说明具体阻塞。

字形越界、文字重叠、清单遗漏／重复、错误字段都会在写出 PNG 前失败。程序执行明确的设计变换，不自动缩字或压扁来应付溢出。倾斜与拉长后的边界也纳入检查，失败时调整区域、换行或构图。

已有输出默认不覆盖；明确替换工作文件时加 `--force`。开发验证可加 `--report checks.json`，普通成图不需要。程序通过只证明技术检查范围，仍须 [检查实际图片](image-production.md)，确认字形、正文阅读、背景对比和原图保留区域。
