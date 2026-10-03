# claude-skills 维护说明

把本机 `~/.claude/skills/` 里有分享价值的 skill 整理成公开 plugin marketplace，GitHub `Elucidator-hky/claude-skills`。

## 结构

- `.claude-plugin/marketplace.json` 列出全部插件，`name` = `elucidator-skills`
- 每个插件一个目录 `plugins/<插件>/`，内含 `.claude-plugin/plugin.json` 和 `skills/<skill>/SKILL.md`
- marketplace 条目的 `name` 与插件 `plugin.json` 的 `name` 保持一致
- skill 自带脚本放 `skills/<skill>/scripts/`，SKILL.md 里用 `${CLAUDE_SKILL_DIR}/scripts/...` 引用

## 从本机搬一个 skill 进来

1. 复制 skill 和它依赖的脚本，脚本改成可直接执行的独立文件
2. 隐私清理：本机路径（`/Users/...`、`~/.config/secrets`）、账号专属地址、本地代理端口、真名、公司名、群名、钉钉 ID 全部换成环境变量或通用描述
3. 跑 `claude plugin validate .` 和 `claude plugin validate ./plugins/<插件>`
4. `claude -p "<触发语>" --plugin-dir ./plugins/<插件> --allowedTools Skill Bash` 实测 skill 能加载、脚本能跑
5. README 加一节：干什么、依赖什么、配哪些环境变量
6. 最后跑 `grep -rnFf .privacy-patterns --exclude=.privacy-patterns --exclude-dir=.git .`，结果为空再提交。`.privacy-patterns` 是本地关键词清单（一行一个），已在 .gitignore 里

## 本机原版与仓库版的关系

本机 `~/.claude/skills/` 和 `~/.claude/scripts/` 是自用原版，仓库是清理后的发布版，两边各自维护；原版有新经验时手动同步过来。

## 进度

- [x] cn-search（search skill + 6 个搜索脚本），2026-10-03 实测通过
- [ ] video-transcript
- [ ] voice-memo-transcript
- [ ] 方法论文章 docs/
