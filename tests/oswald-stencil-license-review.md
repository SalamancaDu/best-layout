# Oswald Stencil 授权复核

核对日期：2026-10-16。结论：当前证据不足，v0.1.0 不打包所选字库；不是认定作者禁止商用。若未来取得明确覆盖该文件的作者声明，再重新评估，不能用第三方的免费标签代替。

核对对象是 [作者仓库中的 TTF](https://github.com/vernnobile/OswaldFont/blob/9dd0521c8c06dd24998fe5d9cd644dab9cbbacca/other/Stencil/Oswald-Stencil.ttf)，35192 字节，SHA-256 为 `bb63e558949a304af38fcb6bd55510374c8e58f2b825848e0c6988ce7ec6651c`。不把普通 Oswald、新版 Stencil 或同名转载字体当作同一个文件。

| 已检查的来源 | 实际观察与限制 |
|---|---|
| [根目录 README](https://github.com/vernnobile/OswaldFont/blob/9dd0521c8c06dd24998fe5d9cd644dab9cbbacca/README.md)、README、3.0/README | 介绍 Oswald 和免费网页使用；没有找到针对所选 Stencil 文件的再分发声明。 |
| [1.0 Bold OFL](https://github.com/vernnobile/OswaldFont/blob/9dd0521c8c06dd24998fe5d9cd644dab9cbbacca/1.0/Bold/FINAL/OFL.txt)、[3.0 OFL](https://github.com/vernnobile/OswaldFont/blob/9dd0521c8c06dd24998fe5d9cd644dab9cbbacca/3.0/OFL.txt) | 普通 Oswald 的许可存在，但不能仅凭同仓库关系认定另一目录的字库也已明确标注在该许可下。 |
| TTF 内嵌 name 表 | 有 Vernon Adams 的版权声明；name ID 13、14（许可说明和许可 URL）未提供。文件存在和能渲染不等于已取得分发依据。 |
| [对应 UFO 的 fontinfo.plist](https://github.com/vernnobile/OswaldFont/blob/9dd0521c8c06dd24998fe5d9cd644dab9cbbacca/other/Stencil/Oswald-Stencil.ufo/fontinfo.plist) | 未找到许可、版权或商标字段；Stencil 目录未找到专属许可证。 |
| [该文件引入提交](https://github.com/vernnobile/OswaldFont/commit/0b732ce7f1916360caaaad62d129812960371c5c)、作者仓库公开 issues | 文件历史只有该引入提交，说明为版本增加；本次公开 issues 查询没有取得相关许可澄清。未联系作者。 |
| 先前保留的第三方游戏 EULA 摘录 | 不是作者的一手授权，撤回此前用它确认 Stencil 可分发的结论。 |

处理：从技能字体清单和维护选择清单移除 Oswald Stencil；删除技能目录中的重复字库及通知副本，本地研究原件保留在不打包、不纳入 Git 的 `tests/font-specimens/`。在用示例改为 WD-XL；历史失败稿只作为历史，不用它们验证当前字体池。发布脚本仅接纳明确列出的 10 款字体，并校验每份原件和许可哈希。
