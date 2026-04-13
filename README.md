# Claude Skills 技能库

一个为 [Claude.ai](https://claude.ai) 准备的社区技能（Skill）集合，按类别整理，可直接下载安装使用。

## 什么是 Claude Skill？

Claude Skill 是一个可安装的指令包，能让 Claude 在特定任务上表现得更专业、更稳定。安装后，Claude 会在合适的时机自动调用对应的 Skill，无需你每次手动描述任务背景。

## 技能分类

| 类别 | 说明 | 技能数量 |
|------|------|----------|
| 📈 [finance](./finance/) | 金融市场分析、选股、数据解读 | 2 |

---

## 如何安装 Skill

### 方法一：下载 `.skill` 文件（推荐）

1. 进入你想安装的技能目录
2. 下载该目录下的 `.skill` 文件
3. 在 Claude.ai 中，进入 **Settings → Skills**
4. 点击 **Upload Skill**，选择下载的 `.skill` 文件
5. 安装完成后，Claude 会在对话中自动识别并调用

### 方法二：手动克隆使用

```bash
git clone https://github.com/YOUR_USERNAME/claude-skills.git
```

然后将对应技能目录的内容上传至 Claude Skills 设置页。

---

## 贡献指南

欢迎提交 PR 贡献新技能！请参考现有技能的目录结构：

```
category/
└── skill-name/
    ├── SKILL.md          # 技能主文件（必须）
    ├── README.md         # 技能说明文档（必须）
    ├── skill-name.skill  # 打包文件，供直接下载（必须）
    └── references/       # 参考资料（可选）
        └── *.md
```

---

## 许可证

MIT License — 自由使用、修改和分发。
