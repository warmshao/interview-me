# InterviewMe

> 把你和 LLM 的对话、以及你的 JD，蒸馏成个人面试复习知识库。

[English](README.md) | [中文](README_zh.md)

用 LLM vibecoding、分析论文、排查问题时，对话里全是知识——但会话一结束就蒸发了。**InterviewMe** 自动（或手动）把这些知识捕获、脱敏、整理成一个本地网站。每个页面都按面试官的思维方式组织：上半部分是学习卡片（一句话定义 / 核心概念 / 对比表格 / 图示 / 关联知识），下半部分是高频面试 Q&A（答案默认折叠可自测，带层层追问）。

**给人复习和备战面试用的，不是给 AI 看的 wiki。**

## 快速安装

把下面这段贴给 Claude Code 或 Codex：

```
Install interview-me from https://github.com/warmshao/interview-me:
clone the repo, then run `python scripts/install.py`.
Follow install.md if anything fails.
```

安装器会：

1. 把 skill 安装到 `~/.claude/skills/interview-me/`
2. 向 `~/.claude/settings.json` 幂等注册 SessionEnd hook（自动备份原配置）
3. 初始化知识库（默认 `~/.interview-me`，可用 `--kb` 自定义）
4. 启动本地服务 **http://127.0.0.1:11123**（`--port` 改端口，`--startup` 开机自启）

## 两种知识来源

| 模式 | 工作方式 |
|---|---|
| **对话蒸馏** | 自动：会话结束时 hook 过滤掉水会话，后台静默提取。手动：对话中输入 `/interview-me`，可带要求（`/interview-me 只提取 RL 部分`） |
| **JD / 面试备战** | 直接贴 JD 或真实面试题：`/interview-me <粘贴 JD>`。它会拆解 JD 考点并排优先级、联网查证答案、按主题写入对应分类，并生成一份**备考路线图**页面（学习顺序 + 模拟面试题） |

写入遵循**先查后写**：已有页面改写合并，只有真正的新子领域才新建。一个 HTML = 一个子领域（如 `kv-cache.html`），页面数量受控。大类（LLM / RL / WAM / VLA …）由模型按需自主创建。对话没有干货时允许零产出。

## 两类知识

- **通用知识** —— 脱敏后的可迁移概念，按大类归档：`<kb>/<大类>/<子领域>.html`
- **项目知识** —— 与你正在做的项目绑定（架构权衡、踩坑、"讲讲你的项目"考点）：`<kb>/projects/<项目>/<主题>.html`。JD 备考路线图也在这里（`projects/jd-<岗位>/`）

首页侧栏分 General / Projects 两个区展示。

## 从"存"到"习"

- **遗忘曲线复习** —— 每个页面都有复习记录（存在浏览器里，无后端）。答对间隔 1→3→7→14→30→60 天递进，答错打回第 1 天，新页面立即到期。侧栏 **Due for review** 和卡片红点告诉你今天该复习什么
- **🎯 Quiz me** —— 首页内嵌全部页面的面试题库。随机出题（到期页面 3 倍权重），点开展示答案，"认识/不认识"的自评直接写入该页复习记录。可按大类/项目/仅到期筛选。全键盘操作：`空格` 翻面 · `1` 认识 · `2` 不认识 · `→` 下一题
- **学习仪表盘** —— 连续打卡天数、今日/累计答题数、到期数、GitHub 风格热力图
- **随处可复习** —— 卡片上、页面内悬浮按钮、Quiz 自评，三处标记同一条记录。页面打印友好：打印时自动展开所有折叠答案，就是一份面试 cheat-sheet

## 浏览器里直接管理

- **删除页面** —— 悬停卡片点 ✕，二次确认后服务端删除并重建目录
- **领域屏蔽** —— 顶栏 Filters 按钮打开标签编辑器，被屏蔽的领域会注入提取 prompt，之后的对话自动跳过
- **亮/暗主题** —— 全站页面同步切换

## 富文本，纯离线

页面支持 LaTeX 公式（`\(...\)`、`$$...$$`）、语法高亮代码块、Markdown 区块——全部由本地 vendor 的 assets 渲染（MathJax-SVG 含完整 TeX 扩展 / highlight.js / marked），零网络依赖。

## 知识库结构

```
~/.interview-me/
├── index.html               # 首页（生成，数据内嵌，双击也能开）
├── index.json               # 机器索引，供去重决策
├── config.json              # 端口、屏蔽领域
├── assets/                  # vendor 的 JS/CSS（公式、高亮、Markdown）
├── LLM/  RL/  WAM/ ...      # 通用大类，模型按需创建
│   └── kv-cache.html        # 子领域页：学习卡片 + 面试 Q&A
├── projects/
│   ├── my-robot/            # 项目知识，一个项目一个文件夹
│   └── jd-some-role/        # JD 备考路线图
└── logs/                    # 提取 prompt 与日志
```

## 常用命令

```bash
python scripts/install.py                 # 安装 / 升级（幂等）
python scripts/install.py --startup       # 安装 + 开机自启服务
python scripts/install.py --uninstall     # 卸载（保留知识库）
python scripts/serve.py start|stop|status # 管理本地服务
python scripts/build_index.py             # 手动重建首页
```

Claude Code 和 Codex 共享同一个服务实例，不会冲突（`start` 幂等）。Codex 没有 SessionEnd hook，只有手动模式——见 [install.md](install.md)。

## 设计原则

- **脱敏**：通用知识剔除项目名、路径、密钥、业务数据
- **先查后写**：对着已有索引去重，合并优先于新建
- **LLM 不碰 UI**：模型只产出内容，首页由脚本确定性生成
- **自包含离线**：每个页面零外部依赖
- **宁缺毋滥**：对话没干货时跳过是正确行为

## License

[MIT](LICENSE)
