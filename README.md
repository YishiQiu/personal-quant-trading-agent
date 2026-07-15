<p align="center">
  <img src="docs/assets/hero.svg" width="100%" alt="Personal Quant Trading Agent" />
</p>

<p align="center">
  <a href="https://github.com/YishiQiu/personal-quant-trading-agent/releases"><img src="https://img.shields.io/github/v/release/YishiQiu/personal-quant-trading-agent?style=flat-square&amp;color=aa8448" alt="最新版本" /></a>
  <a href="https://github.com/YishiQiu/personal-quant-trading-agent/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/YishiQiu/personal-quant-trading-agent/ci.yml?branch=main&amp;style=flat-square&amp;label=build" alt="构建状态" /></a>
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-15314f?style=flat-square" alt="MIT License" /></a>
</p>

<p align="center">
  <a href="https://www.python.org/"><img src="https://img.shields.io/badge/Python-3.11%2B-15314f?style=flat-square&amp;logo=python&amp;logoColor=white" alt="Python 3.11+" /></a>
  <a href="https://react.dev/"><img src="https://img.shields.io/badge/React-18-15314f?style=flat-square&amp;logo=react&amp;logoColor=white" alt="React 18" /></a>
  <a href="https://github.com/YishiQiu/personal-quant-trading-agent/generate"><img src="https://img.shields.io/badge/Use_this_template-创建自己的版本-aa8448?style=flat-square&amp;logo=github&amp;logoColor=white" alt="使用项目模板" /></a>
</p>

<h3 align="center">面向 A 股尾盘决策的个人量化研究智能体</h3>

<p align="center">
  不是自动交易机器人。负责浏览市场、整理证据与解释机会，最终决定始终由人完成。
</p>

<p align="center">
  <a href="#-快速开始">快速开始</a> ·
  <a href="#-创建自己的版本">创建自己的版本</a> ·
  <a href="#-形态算法">算法定义</a> ·
  <a href="#-数据与模型">数据边界</a> ·
  <a href="#-路线图">路线图</a>
</p>

<br />

<table width="100%">
  <tr>
    <td align="center" width="25%"><strong>🌐 全市场</strong><br/><sub>浏览 5,000+ 只 A 股</sub></td>
    <td align="center" width="25%"><strong>⚙️ 规则漏斗</strong><br/><sub>价格、板块、流动性、形态</sub></td>
    <td align="center" width="25%"><strong>🧠 深度研究</strong><br/><sub>历史、新闻、风险、DeepSeek</sub></td>
    <td align="center" width="25%"><strong>👤 人工决策</strong><br/><sub>不自动下单，不承诺收益</sub></td>
  </tr>
</table>

<p align="center">
  <img src="docs/assets/dashboard.png" width="94%" alt="Personal Quant Trading Agent 研究工作台" />
</p>

<br />

<h2 align="center">研究流程</h2>
<p align="center"><sub>从 5,000+ 只股票到少数候选，每一步都有明确边界</sub></p>

<table width="100%">
  <tr>
    <td align="center" width="20%"><sub>01</sub><br/><strong>全市场</strong><br/><sub>完整收盘快照</sub></td>
    <td align="center" width="20%"><sub>02</sub><br/><strong>用户条件</strong><br/><sub>价格 · 板块 · 流动性</sub></td>
    <td align="center" width="20%"><sub>03</sub><br/><strong>形态门控</strong><br/><sub>完美十字 · 锤子线</sub></td>
    <td align="center" width="20%"><sub>04</sub><br/><strong>深度研究</strong><br/><sub>历史 · 新闻 · 风险</sub></td>
    <td align="center" width="20%"><sub>05</sub><br/><strong>人工决策</strong><br/><sub>综合评分 · 不自动下单</sub></td>
  </tr>
</table>

<p align="center">
  <strong>规则负责筛选，AI 负责研究，人负责决策。</strong><br/>
  <sub>LLM 只读取已经入围的候选股，不能绕过规则门控或风险否决。</sub>
</p>

<br />

<h2 align="center">v1.1.0 · 中文化与模板化</h2>
<p align="center">不改变选股逻辑，只让项目更容易读懂、复刻和继续开发。</p>

<table width="100%">
  <tr>
    <td align="center" width="33.33%"><strong>中文说明</strong><br/><sub>模块、算法与配置注释统一整理</sub></td>
    <td align="center" width="33.33%"><strong>集中品牌配置</strong><br/><sub>一个文件管理名称与首屏文案</sub></td>
    <td align="center" width="33.33%"><strong>完整改版指南</strong><br/><sub>品牌、策略、数据源与 Agent</sub></td>
  </tr>
  <tr>
    <td align="center" width="33.33%"><strong>项目模板</strong><br/><sub>一键创建没有原提交历史的新仓库</sub></td>
    <td align="center" width="33.33%"><strong>版本统一</strong><br/><sub>Python、API 与前端保持一致</sub></td>
    <td align="center" width="33.33%"><strong>质量验证</strong><br/><sub>测试、静态检查、构建与 CI</sub></td>
  </tr>
</table>

<p align="center"><sub>默认扫描 3–100 元，并纳入创业板和科创板；所有条件都可以在扫描前调整。</sub></p>

## 🚀 快速开始

需要 Python 3.11+ 与 Node.js 20+。

```bash
git clone https://github.com/YishiQiu/personal-quant-trading-agent.git
cd personal-quant-trading-agent

python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,api,data]'
cp .env.example .env
uvicorn 'trading_agent.api:create_app' --factory --reload
```

另开一个终端：

```bash
cd frontend
npm ci
npm run dev
```

| 入口 | 地址 |
| --- | --- |
| 研究工作台 | [http://localhost:5173](http://localhost:5173) |
| API 文档 | [http://localhost:8000/docs](http://localhost:8000/docs) |
| 无密钥演示 | `trading-agent research --provider demo` |

<details>
<summary><strong>使用最近完整收盘快照</strong></summary>

```bash
trading-agent capture-close --provider sina_free
trading-agent research --provider sina_free
```

系统只把 09:15 前或 15:00 后取得的完整数据写入正式收盘快照，盘中数据不会覆盖它。公开免费源适合个人低频研究与回放，不等同于授权实时行情。

</details>

## 🛠 创建自己的版本

不需要从头拆代码。GitHub 会用当前项目创建一份没有原提交历史的新仓库。

<p align="center">
  <a href="https://github.com/YishiQiu/personal-quant-trading-agent/generate"><strong>使用这个模板创建项目 →</strong></a>
</p>

<table width="100%">
  <tr>
    <td align="center" width="33.33%"><sub>第一步</sub><br/><strong>换成自己的品牌</strong><br/><sub><code>frontend/src/branding.ts</code></sub></td>
    <td align="center" width="33.33%"><sub>第二步</sub><br/><strong>调整研究参数</strong><br/><sub><code>configs/</code></sub></td>
    <td align="center" width="33.33%"><sub>第三步</sub><br/><strong>替换数据源与 Agent</strong><br/><sub><a href="docs/customization.md">复刻与改版指南</a></sub></td>
  </tr>
</table>

> [!TIP]
> 先用 `demo` 数据源跑通页面，再接入自己的行情服务。这样可以把界面问题与数据接口问题分开排查。

## 📐 形态算法

全部使用 OHLC 数学计算，不使用图片识别。设总振幅 `R = H - L`，两类形态都要求 `C > O` 且 `R / O >= 3%`。

| 形态 | 默认定义 |
| --- | --- |
| 阳线完美十字 | `实体 / R ≤ 2%`；上下影各占 `R ≥ 45%`；影线差 `≤ 6%` |
| 阳线锤子 | 实体占 `R` 的 `3%–30%`；下影至少为实体 `2 倍` 且占 `R ≥ 60%`；上影不超过实体 `0.5 倍` |

T 字线和明显不对称的十字会被排除。阈值集中在 [`configs/workflow.yaml`](configs/workflow.yaml)，基础扫描条件位于 [`configs/market_scanner.yaml`](configs/market_scanner.yaml)。

## 🔌 数据与模型

<table width="100%">
  <tr><th>类别</th><th>当前来源</th><th>使用位置</th></tr>
  <tr><td>全市场 / 日 K</td><td>新浪、东方财富</td><td>规则扫描与候选历史</td></tr>
  <tr><td>公司公告</td><td>巨潮资讯 CNINFO</td><td>候选股证据</td></tr>
  <tr><td>个股新闻</td><td>东方财富 / AKShare</td><td>候选股证据</td></tr>
  <tr><td>补充新闻</td><td>Tushare，可选</td><td>取决于账号权限</td></tr>
  <tr><td>研究模型</td><td>DeepSeek，可选</td><td>只读取已筛选候选</td></tr>
</table>

<details>
<summary><strong>启用 DeepSeek</strong></summary>

在本地 `.env` 填入：

```dotenv
DEEPSEEK_API_KEY=your_key_here
```

密钥只存在后端环境变量中，不会发送给前端。`.env`、行情快照、新闻缓存和 SQLite 数据库均已被 Git 忽略。

</details>

> [!WARNING]
> 免费网页接口可能限流、改版、延迟或缺失。系统会显式失败或降级，不把部分数据伪装成完整市场；生产和商业用途应替换为有授权的数据源。

## 🧩 工程结构

<details>
<summary><strong>查看目录与模块边界</strong></summary>

```text
TradingAgent/
├── configs/                    # 扫描、形态、新闻与模型配置
├── docs/                       # 架构、工作流与数据接入说明
├── frontend/                   # React + TypeScript 研究工作台
├── src/trading_agent/
│   ├── providers/              # 可插拔行情 Provider
│   ├── market_scanner/         # 基础漏斗与形态门控
│   ├── agents/                 # 趋势、量能、催化、风险、LLM、决策
│   ├── news/                   # 新闻与公告 Provider
│   ├── orchestrator/           # 两阶段研究工作流
│   ├── api.py                  # FastAPI 接口
│   └── cli.py                  # 命令行入口
└── tests/                      # 单元测试与工作流测试
```

进一步阅读：[`复刻与改版`](docs/customization.md) · [`架构说明`](docs/architecture.md) · [`工作流说明`](docs/workflow.md) · [`数据接入清单`](docs/data-requirements.md)

</details>

## 🗺 路线图

- [x] 全市场完整快照与可配置基础漏斗
- [x] 严格完美十字 / 锤子线门控
- [x] 候选历史行情、新闻公告、风险与可选模型研究
- [x] FastAPI、React 工作台、SQLite、测试与 CI
- [ ] 板块强度、资金流与基本面的生产级数据源
- [ ] 次日表现归因与个人评分权重学习
- [ ] LangGraph 持久化编排、回测和策略版本管理
- [ ] PostgreSQL、通知、桌面端与多模型适配

## 🤝 参与项目

欢迎贡献数据 Provider、形态测试、界面和文档。请先阅读 [`CONTRIBUTING.md`](CONTRIBUTING.md)；版本变化记录在 [`CHANGELOG.md`](CHANGELOG.md)，安全问题请按 [`SECURITY.md`](SECURITY.md) 私下报告。

本项目仅用于个人研究、工程实践和教育交流，不构成投资建议、收益承诺或自动交易服务。基于 [MIT License](LICENSE) 开源。

<div align="center">
  <sub>为有纪律的研究而建，不为自动化投机而生。</sub>
</div>
