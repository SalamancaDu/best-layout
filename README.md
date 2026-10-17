# best-layout

把正式内容排成清楚、有秩序的图片。默认结合日式编辑设计的精细文字与留白，以及瑞士设计的网格、层级和对齐。

适用于海报、封面、社媒图文、信息图和单页演示。成功制图时只展示最终位图，画面保留正式文案，不混入设计说明、参数或提示词；不生成 SVG 或 HTML 预览页。

## 使用

在能读取本项目并运行本地脚本的代理中，直接引用 [Skill 入口](skills/best-layout/SKILL.md)。需要摄影或插画时，宿主还须提供图像生成／编辑能力：

```text
请按 skills/best-layout/SKILL.md 制作一张 3:4 音乐会海报，用于手机信息流。
正式文案只有：
夜行音乐会
让节拍穿过街道
2026.12.05
19:30—21:00
回声剧场
凭票入场
不要增加其他文字，完成后只展示图片。
```

上例为虚构练习内容，不代表真实活动。真实任务使用自己的准确内容；可以直接给用途与文案，不必先确定字体、配色和构图。有品牌或素材约束时一并提供。

如已自行安装到宿主支持的 Skill 目录，可用 `$best-layout` 调用；本项目不会自动进行全局安装。复制时保持整个 `skills/best-layout` 文件夹完整。Codex 的展示配置已提供，自动选择保持默认开启。

用户明确要求诊断、方案、提示词或解释时，交付相应内容，不额外生成图片。普通制图不要求用户学习内部流程，也不附加固定审批轮次。

## 方法与工具

- [构图与秩序](skills/best-layout/references/composition.md)：从内容建立网格，处理留白、对比、图文关系和横竖适配。
- [文字排版](skills/best-layout/references/typography.md)：字号角色、标点、行距、字距、中英混排和真实日文。
- [图片制作与检查](skills/best-layout/references/image-production.md)：准确文案与指令分离、实际成图检查、限定范围修正。
- [来源索引](skills/best-layout/references/sources.md)：八本日本／瑞士设计参考和排版资料，逐项标明实际阅读范围。

正式文字使用附带的 10 款原始字体：思源黑体 Bold、思源宋体 Heavy、霞鹜文楷 GB、标小智无界黑、香萃等粗宋、齊伋體、得意黑、WD-XL 滑油字 SC、霞鹜漫黑、缝合像素字体 12px。字体与原始许可证约 103.5 MiB，位于技能目录内，不需安装到系统。Oswald Stencil 因所选文件的分发授权尚未确认，已从首版排除；英文／数字示例改用 WD-XL。来源、字重、适用范围及缺字限制见 [真实字体排字](skills/best-layout/references/local-typesetting.md)。

排字复用本项目已有的 Python + Playwright + Chromium 技术栈。代理形成文案与布局配置，脚本检查缺字、漏项、重复项、文字溢出和重叠，再合成 PNG。纯文字图无需生图工具；需要摄影／插画时，宿主生成无字素材后再排字。本项目不附带模型、账号或外部模型 API 客户端，不自动下载浏览器或安装依赖。

标题先从合适字库的原生比例建立表达，需要时自主倾斜、拉宽、压窄或纵向拉长；内部与原形比较后保留有效处理，变差则减弱或撤回。正文和辅助信息按阅读任务处理。变换在真实字库排印时执行，保留准确原文，并重新计算换行、对齐和边界；不要求用户逐项指定处理参数。

```sh
python skills/best-layout/scripts/compose.py --check-env
python skills/best-layout/scripts/compose.py layout.json final.png
```

可用 `--channel chrome`／`--channel msedge` 复用系统浏览器，或用 `--chromium "实际路径"` 指定。缺运行环境的安装说明见上述参考。当前验证为 Windows 本机；路径设计不依赖此电脑，尚未实测 macOS／Linux。字体文件和程序检查不能代替文案、对比度及观看尺寸核对。

## 验证

[测试输入](tests/cases.md) 包含原有四例，以及正常调用的音乐会海报、20 项完整文案的手机活动指南、指定高饱和品牌色的纯文字海报。[验证记录](tests/validation.md) 保留失败首稿、修正过程、最终图片和手机显示截图，区分结构检查与实际观察。

当前真实字体路径另有 [7 张排字作品与换行用例](tests/typesetting/)、[10 款字库检查页](tests/typesetting/selected-fonts.png)、[排字回归](tests/test_typesetting.py)和 [发布包测试](tests/test_release.py)。包括按用户反馈恢复原生比例、减轻倾斜的[夜跑海报](tests/typesetting/forward-poster.png)，以及压窄拉高的[观察展海报](tests/typesetting/light-poster.png)。回归覆盖字体加载、文案完整性、成对省略号／破折号、数字与前后缀、中文组合单位、词内撇号、不换行空格、变换后的换行／对齐／边界、缺字／溢出拦截、透明合成及未变形文字的像素保持；发布测试从解压目录验证运行和同一组换行用例，并确认失败任务不会替换已有图片。普通测试不覆盖已审阅的样图。夜跑初稿虽通过技术检查，仍因字形过扁被用户否定，过程见验证记录。

[显示检查脚本](tests/inspect_images.py) 使用本机已有的 Pillow、Playwright 和 Chromium，直接打开 PNG 并截取指定显示宽度的图片；不修改原图、不安装依赖，也不自动判断文案或设计通过。它仅供开发验证，技能运行不依赖这个脚本。

```powershell
python -X utf8 tests/inspect_images.py tests/outputs/repair-guide.png --width 390 --output-dir tests/inspection
```

若当前 Playwright 没有默认浏览器路径，用 `--chromium "已安装的 Chromium 可执行文件路径"` 指定。本次实际检查了 390 像素宽，密集页另检查了 360 像素宽；这些是浏览器显示模拟，不是真机或用户盲测。

本仓库维护任务可以报告文件与验证结果；“只展示图片”约定用于 Skill 的成功制图交付。示例的研究与验证记录不会写进最终图片。

## v0.1.0 本地发布包

```sh
python scripts/build_release.py
```

输出 `dist/best-layout-v0.1.0.zip` 及同名 `.zip.sha256`，需要重建已有包时加 `--force`。脚本只在本地打包，不上传、安装、提交或发布。解压后得到完整的 `best-layout/`，可复制到宿主支持的 Skill 目录，或直接引用其中的 `SKILL.md`。环境准备及命令见包内 `references/local-typesetting.md`；`assets/examples/poster.json` 可用于首次运行。

包内只有技能入口、Codex 配置、参考文档、排字脚本、最小示例、10 款原始字体及许可证。打包时核对许可、字体哈希和内部链接，未列入清单的字体会阻止打包。未携带 Python、Playwright、浏览器、研究下载、历史样图或测试缓存，首次使用仍需具备运行环境。公开源码时不要手工加入已忽略的 `tests/font-specimens/`；其中保留了历史候选与未确认授权的研究原件。

维护检查复用本机已有的 Pillow、Playwright 与 Chromium；测试依赖未随技能打包：

```sh
python -X utf8 tests/test_typesetting.py
python -X utf8 tests/test_release.py
```

若没有默认浏览器，先将 `BEST_LAYOUT_CHROMIUM` 设为已安装的 Chromium 可执行文件。当前实测范围是 Windows，本地解压运行不等于干净机器安装或跨平台验收。

## 许可证

原创代码、Skill 与文档采用 [MIT](LICENSE)。字体另按各自的 OFL-1.1 分发，版权和许可清单见 [第三方说明](skills/best-layout/THIRD_PARTY_NOTICES.md)。独立技能目录也保留 MIT 副本，复制该目录不会漏掉项目许可。[Oswald Stencil 复核记录](tests/oswald-stencil-license-review.md)说明了首版排除依据。
