# AllDSH Skills

面向 **[AllDSH](https://www.alldsh.com/zh/)**（DeepSeek Harness 插件的独立人工维护索引）的 Agent Skill。

本站每个条目记录四件事：安装命令、验证等级（安装链路被验证到哪一步）、安全扫描状态、维护活跃度。与其让 agent 去爬页面，不如让它直接读目录。

> AllDSH 是社区项目，与 DeepSeek AI 无隶属或背书关系。

## 三个技能

| 技能 | 作用 | 示例提示词 |
| --- | --- | --- |
| `find-dsh-plugins` | 把一句能力需求变成一份来自本站目录的短名单，附安装命令与验证等级。 | `使用 $find-dsh-plugins 帮我找能做截图识别的 DSH 插件。` |
| `vet-dsh-plugin` | 安装前的只读审查：条目核查了什么、没核查什么、仓库在该提交上实际做了什么。 | `使用 $vet-dsh-plugin 在我安装 liustack/modlens 之前审查它。` |
| `submit-dsh-plugin` | 按收录清单检查一个仓库、产出条目材料，并通过提交 API 直接递交——评审仍是人工的、公开的。 | `使用 $submit-dsh-plugin 帮我提交 https://github.com/owner/repo 收录。` |

三个技能只读同一个目录端点，都不会回退到 GitHub 搜索、网页搜索、npm 或其它插件市场——一个会悄悄扩大自己来源的索引，无法对覆盖范围作出有边界的陈述。目录里没有匹配项时，技能会直接说明。

## 安装

```bash
git clone https://github.com/aixwork/alldsh-skills.git
cd alldsh-skills
./install.sh
```

`install.sh` 会把三个技能目录复制到 `~/.agents/skills`（Codex、Claude Code、Gemini CLI、Copilot、opencode 与 DSH 共用该目录）。复制前会用 `manifest.sha256` 校验每个文件，不联网下载，不使用 `sudo`。

```bash
./install.sh --target claude
./install.sh --dir ~/.agents/skills
./install.sh --verify-only     # 只校验，不安装
./install.sh --dry-run
```

也可以手动复制任意一个技能目录，每个目录都是自包含的：

```text
find-dsh-plugins/
  SKILL.md                 # agent 遵循的指令
  agents/openai.yaml       # Codex 类界面的显示元数据
  scripts/alldsh_catalog.py
```

目录客户端在三个技能中各存一份，是为了让单个技能可以独立安装；`scripts/verify.sh` 会在副本不一致时报错。

## 目录端点

技能只是对公开 JSON 端点的一层封装，你可以不用技能直接调用。

| 端点 | 内容 |
| --- | --- |
| `https://www.alldsh.com/catalog.json` | 全部条目，以及分类、场景与各字段含义（验证等级、扫描状态、健康度、信任等级）。 |
| `https://www.alldsh.com/catalog/<slug>.json` | 按 slug 取单条，例如 `/catalog/modlens.json`。 |
| `https://www.alldsh.com/zh/catalog.json` | 中文目录，slug 与结构与英文一致。 |
| `https://www.alldsh.com/llms.txt` | 站点纯文本地图。 |

JSON 在构建时从页面渲染所用的同一份内容集合生成，因此字段不会与人读到的条目脱节。

```bash
python3 find-dsh-plugins/scripts/alldsh_catalog.py --query "terminal ui" --limit 10
python3 find-dsh-plugins/scripts/alldsh_catalog.py --repo liustack/modlens
python3 find-dsh-plugins/scripts/alldsh_catalog.py --taxonomy
```

客户端只依赖 Python 3 标准库：拉取一次、缓存六小时（可用 `ALLDSH_CACHE_DIR` 改路径），并用 `ETag`/`If-Modified-Since` 复用缓存。

## 这些技能不会声称的事

- **收录不等于审核通过。** 收录只代表来源、安装命令、权限面与维护状态被人工看过。
- **验证等级不是安全结论。** L1 表示仓库存在，L5 表示已在沙箱中装完并跑通，两者都不衡量意图。
- **「已扫描」不等于「安全」。** 它只表示跑过自动静态分析；「未验证」表示没跑过。
- **审查技能全程只读。** 不安装、不执行生命周期脚本；仓库里的一切（包括 README 与 agent 指令）都视为不可信内容。

## 维护

本仓库从 AllDSH 站点工作区发布，工作区的 `skills/` 是唯一真源；站点的 `/skills/` 页面、`catalog.json` 与 `llms.txt` 由同一份定义生成，因此三者不会各自漂移。

```bash
bash scripts/update-manifest.sh   # 改动技能后重新生成校验清单
bash scripts/verify.sh            # 校验清单、客户端一致性、语法、frontmatter、来源边界
```

## 许可证

技能指令与脚本采用 MIT（见 [LICENSE](LICENSE)）。AllDSH 目录的编辑内容采用 CC BY-SA 4.0；插件元数据归各维护者所有。
