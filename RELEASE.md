# 发布清单

## 更新内容和样例

1. 更新 `skills/best-layout/SKILL.md` 中的 `metadata.version`。
2. 更新版式模式目录和实际样例目录。
3. 为新增样例保留配置、PNG、检查报告和 SHA-256 关系。
4. 确认远程参考图片、未核实字体和测试缓存没有进入技能目录或发布包。

## 验证

```sh
python -X utf8 scripts/verify_layout_catalog.py
python -X utf8 tests/test_layout_catalog.py
python -X utf8 tests/test_release.py
```

如果修改了 `compose.py`、`render_canvas.js` 或字体排字规则，再运行对应的排字回归并查看实际 PNG。中文正文、数字单位、标点、标题字形和实际观看尺寸分别检查。

## 本地打包

```sh
python -X utf8 scripts/build_release.py --force
```

脚本从 `SKILL.md` 的 `metadata.version` 读取版本，生成 `dist/best-layout-v{version}.zip` 和同名 `.zip.sha256`。打包后检查 ZIP CRC、文件清单、字体许可证、内部链接、版式目录和独立解压运行。

## 同步安装版

测试通过后，将项目内的 `skills/best-layout/` 与本机安装目录同步，并再次比较文件哈希。同步前保留安装目录中与当前项目无关的改动。

## GitHub Release

准备好本地包、校验文件、README、许可证和变更说明后，再单独创建 GitHub Release。Release 附件只上传已经核验的 ZIP 和 `.sha256`，仓库历史不提交 `dist/` 中的压缩包。
