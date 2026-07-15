# 系统架构

系统是人工决策的研究助手，不包含下单、券商账户或自动交易能力。

```text
                    ┌──────────────────────────────────┐
                    │ 收盘后全市场日 K 快照（Provider） │
                    └────────────────┬─────────────────┘
                                     ↓
                 Python Market Scanner（全市场确定性规则）
                                     ↓
            用户价格区间 / 板块范围且基础规则通过的完整股票池（不截断）
                                     ↓
           Pattern Gate：最近完整日 K 的阳线完美十字 / 阳线锤子识别
                                     ↓
                    Research Pool：全部形态命中候选股
                                     ↓
         ┌──────────────┬─────────────┬──────────────┬─────────────┐
         ↓              ↓             ↓              ↓
   K线趋势 Agent    量能 Agent    新闻证据 Agent     资金基本面风险 Agent
         └──────────────┴─────────────┴──────────────┴─────────────┘
                                     ↓
                    可选 LLM 研究 Agent（结构化 JSON）
                                     ↓
          Decision Agent（权重、阈值、风险否决、最终排序）
                                     ↓
              Markdown 报告 + SQLite 推荐记录 + Learning 标签
```

## 已实现模块

- `providers/`：市场快照与候选股研究上下文的插件接口；`demo` 可运行，`eastmoney_free` 以低频分页、重试、完整性校验与原始快照缓存实现免费链路，`akshare` 保留为可选兼容层。
- `market_scanner/` 与 `features/`：全市场初筛、已收盘日 K 的阳线完美十字/阳线锤子数学计算。
- `agents/`：六个独立 Agent，统一产生分数、置信度、证据、风险和否决标记；`news/` 以 CNINFO 公告与 AKShare/东方财富个股新闻在候选池后采集可追溯的免费新闻证据，Tushare 保留为可选插件。
- `orchestrator/`：可执行同步工作流，以及对应的节点/边定义；其契约可直接映射为 LangGraph 图。
- `reports/`、`storage/`、`learning/`、`scheduler/`：报告、SQLite 留档、次日表现标签，以及收盘快照/盘前研究时间窗保护。
- `api.py`、`cli.py` 与 `frontend/`：FastAPI、命令行与 React + TypeScript 仪表盘。前端只消费前收盘研究 API，不直接访问任一行情源。

## 明确的边界

- `MarketScanner` 禁止 LLM 和逐股外部调用；它只使用一次全市场快照。
- `PatternGate` 默认只使用已缓存的前一交易日完整开、高、低、收盘价，不把盘中形态误称为收盘 K 线。
- 免费 Provider 必须返回完整且通过校验的全市场快照；数量、代码唯一性、有效价格比例或候选股历史日 K 不达标时，工作流直接失败，不生成推荐。
- 候选股历史数据、新闻、板块、资金和基本面在研究池形成后才加载。新闻源失败时采用 fail-soft 策略：保留“缺少催化证据”的风险，不阻断日 K 研究；成功抓到的原始归因证据保留在 `data/raw_news/`。
- LLM 只能分析结构化候选证据；`DecisionAgent` 保持规则化，且任一 Agent 的 `veto=true` 都可否决。
- 当前评分阈值只是可运行默认值，未经过回测，不能作为交易策略承诺。

## LangGraph 与前端

项目将 LangGraph 保留为可选依赖：当前同步工作流用于先验证领域边界与测试，`orchestrator/definition.py` 已固化图节点和并行分支。接入真实 API 并安装 `.[agents]` 后，应将这些节点映射为 LangGraph，以获得中断恢复、持久状态和可视化追踪。

React 前端已实现为独立 Vite 工程。它先调用 `/api/v1/pattern-scan/sina_free` 直接展示全量阳线完美十字/阳线锤子命中，再按需调用 `/api/v1/research/sina_free` 进入深度研究；API 自动解析最近的完整新浪收盘快照，避免浏览器直接访问行情源或意外使用盘中报价。当前稳定资源是 `/health`、`/api/v1/market-scan/{provider}`、`/api/v1/pattern-scan/{provider}` 与 `/api/v1/research/{provider}`。
