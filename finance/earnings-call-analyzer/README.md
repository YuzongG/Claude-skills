# 📋 财报电话会深度分析 Skill

**earnings-call-analyzer** — 输入股票代码，自动抓取最新一次财报电话会议内容，按专业投资研究框架输出完整中文分析报告。

---

## 功能概览

- ✅ 自动搜寻最新一季财报逐字稿或摘要
- ✅ 七大章节完整输出，结构固定、不遗漏
- ✅ 管理层语气五级判定（极度乐观→防御回避）
- ✅ Q&A 精华萃取 + 三色信号判读
- ✅ 八维投资机会侦测（订单落差、定价权、客户行为转变等）
- ✅ 投资意涵总结（基本面方向、风险、催化剂）
- ✅ 全程繁体中文输出，专业术语保留英文

---

## 安装方法

1. 下载 [`earnings-call-analyzer.skill`](./earnings-call-analyzer.skill)
2. Claude.ai → **Settings → Skills → Upload Skill**
3. 安装完成 ✓

---

## 触发方式

```
帮我分析 NVDA 最新的财报
TSMC 上季业绩怎么样？
分析一下 AAPL 的 earnings call
幫我看 2330 的法說會
```

---

## 输出结构

| 章节 | 内容 |
|------|------|
| 一、管理层前景观点 | 2-3句概括 + 语气等级标注 |
| 二、核心重点与商业逻辑 | 3-5个 bullet，含因果分析 |
| 三、关键财务数据 | 营收/毛利率/EPS/FCF/Guidance 等 |
| 四、管理层语气与态度 | 信心领域、刻意淡化领域、宏观观点 |
| 五、Q&A 精华 | 3-5个热点议题 + 🟢🟡🔴 信号判读 |
| 六、投资机会侦测 | 八维信号扫描（订单、定价权、客户行为等） |
| 七、投资意涵 | 结论、基本面方向、风险、催化剂 |

---

## 文件结构

```
earnings-call-analyzer/
├── SKILL.md                          # 技能主文件
├── README.md                         # 本说明文档
├── earnings-call-analyzer.skill      # 可直接安装的打包文件
└── references/
    ├── financial-terms.md            # 财务术语中英对照表
    └── signal-rubric.md              # 投资信号评分细则
```

---

## 数据来源

| 功能 | 数据源 |
|------|--------|
| EPS 实际值 vs 预期值 | **[Finnhub API](https://finnhub.io)** `/stock/earnings`（推荐，需免费 Key）|
| 关键财务指标 | Finnhub `/stock/metric`（毛利率、营业利润率、P/E 等） |
| 财报相关新闻 | Finnhub `/company-news` |
| 公司基本资料 | Finnhub `/stock/profile2` |
| 逐字稿/管理层叙述 | 网络搜索（SeekingAlpha、Motley Fool 等） |

> 无 Finnhub API Key 时全程使用网络搜索替代，EPS surprise 数据需手动查找。

## 注意事项

- 建议配置 Finnhub API Key（免费），可自动获取 EPS 超预期幅度、历史财季对比等结构化数据
- 财报逐字稿通常在电话会结束后 24-48 小时内公开
- 若逐字稿尚未公开，将以新闻稿 + 媒体报导替代，并注明
- 用户也可直接上传逐字稿文件，Claude 会以上传内容为主
- **本工具仅供投资研究参考，不构成投资建议**

---

## 许可证

MIT License
