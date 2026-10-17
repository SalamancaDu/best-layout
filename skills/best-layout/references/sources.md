# 来源索引

核对日期：2026-10-16。以下链接在本项目规划期间查阅；本 Skill 是原创方法归纳，不是书籍译文、摘要合集或书页复刻。

**证据范围**：书籍公开介绍和目录只能证明主题与范围，不能证明已经读过书中案例或得到作者对本 Skill 的认可。未取得完整正文的书籍不标为全文阅读；设计史不作为生成图片的必要前置流程。

## 日本设计参考

| 书籍与来源 | 已查阅范围 | 在本 Skill 中的用途 |
|---|---|---|
| gaatii 光體，《日本版面的法則》，原點；[书籍页面](https://www.books.com.tw/products/0010993011)、[出版社公开文章](https://vocus.cc/article/611dc269fd89780001885b81) | 中文书籍公开介绍，以及出版社关于八种构成手法的文章；未读完整书籍 | 五大要素和构成手法的观察框架。它是中文日本案例解析书，不标为日本原版著作。 |
| 筒井美希，《なるほどデザイン》，MdN，2015；[出版社页面](https://books.mdn.co.jp/books/3215303004/) | 官方介绍与公开目录；未读完整书籍 | 从编辑目的理解设计、信息选择与表达。具体执行规则由本项目归纳。 |
| ingectar-e，《けっきょく、よはく。余白を活かしたデザインレイアウトの本》，ソシム，2018，ISBN 978-4-8026-1169-5；[出版社页面](https://www.socym.co.jp/book/1169) | 官方介绍与目录；未读完整书籍 | 留白与字距、行距、裁切、焦点、分组及视线的关联。 |
| ingectar-e，《ほんとに、フォント。フォントを活かしたデザインレイアウトの本》，ソシム，2019，ISBN 978-4-8026-1208-1；[出版社页面](https://www.socym.co.jp/book/1208) | 官方介绍与目录；未读完整书籍 | 字体选择、字重、字距、行距、辨认度和混排的任务化检查。 |
| 《デザイナーズハンドブック レイアウト編》，PIE International，2015，ISBN 978-4-7562-4662-2；[出版社页面](https://pie.co.jp/book/i/4662/) | 官方介绍与书目信息；未逐页分析页面样张，未读完整书籍 | 版面占比、网格、字号差等基础概念。 |

## 瑞士设计参考

| 书籍与来源 | 已查阅范围 | 在本 Skill 中的用途 |
|---|---|---|
| Josef Müller-Brockmann，《Grid Systems in Graphic Design》，Niggli，1981，ISBN 978-3-7212-0145-1；[出版社页面](https://niggli.ch/en/products/rastersysteme-fur-die-visuelle-gestaltung) | 官方介绍与书目信息；未读完整书籍 | 将网格视为组织内容与保持一致的工具，而非外观模板；本项目不照搬书中的具体网格案例。 |
| Emil Ruder，《Typography. A Manual of Design》，Niggli，1967，ISBN 978-3-7212-0043-0；[出版社页面](https://niggli.ch/en/products/typographie) | 官方介绍与书目信息；未读完整书籍 | 文字结构、可读性、节奏与比例的共同检查。 |
| Armin Hofmann，《Graphic Design Manual》，Niggli；[出版社页面](https://niggli.ch/en/products/methodik-der-form-und-bildgestaltung) | 官方介绍与书目信息；未读完整书籍；页面描述原作出版于 1965 年及后续版本 | 对比、形式、节奏与构成的整体关系，不把“减少元素”误解为取消表达。 |

## 排版技术资料

- [W3C 中文排版需求 CLReq](https://www.w3.org/TR/clreq/)：已查阅行首行尾禁则及 6.1.2.1、6.1.2.2 的符号分离规则，用于省略号／破折号成组、数字前后缀与单位的换行修复；未逐节穷尽审读，也不宣称脚本实现了完整 CLReq。
- [W3C 日文排版需求 JLReq](https://www.w3.org/TR/jlreq/)：已查阅行首／行尾禁则相关段落，其他章节按需查询；日文规则不能不加区别地套到中文。
- [MoMA：The New Typography](https://www.moma.org/calendar/exhibitions/1013)：已查阅公开展览说明。用于区分 1920—1930 年代新字体运动与后来瑞士国际主义的发展，不把两者当作同一时间、同一来源的事件。

## 归纳与引用方式

真实字体来源、版本及原始许可证见 [字库清单](../assets/fonts/manifest.json)，用法与限制见 [真实字体排字](local-typesetting.md)。已核对随字库保存的许可证和实际字体元数据，不只依赖字体推荐网站的“免费”标签。分发说明依据 [SIL 官方 OFL 使用说明](https://openfontlicense.org/how-to-use-ofl-fonts/)；运行接口参考 [Playwright 浏览器文档](https://playwright.dev/python/docs/browsers)、[Canvas letterSpacing](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/letterSpacing)、[transform 矩阵变换](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/transform)和 [measureText 字形测量](https://developer.mozilla.org/en-US/docs/Web/API/CanvasRenderingContext2D/measureText)。仅查阅本项目使用的相关说明，不声称穷尽兼容性。

五大要素、八种手法、具体情境的结构选择及检查方法是本项目组织知识的方式，不宣称它们是唯一的行业分类，也不将本项目规则伪装为书中逐字结论。构图参考中的音乐会、手机活动指南与品牌文字展决策示例来自本项目的原创实测及修正，不冒充这些书中的案例。

正常制图不把来源、作者、流派名或研究说明写进画面。用户明确要求研究或解释时再提供出处。图片参考只提取结构和关系；不复制完整书页、图版、现成作品或未获授权的字体文件。
