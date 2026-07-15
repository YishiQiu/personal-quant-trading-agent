# 复刻与改版指南

这份项目把行情接入、筛选规则、研究流程和页面展示分开了。你可以保留现有工作流，只替换品牌和参数；也可以逐步换掉数据源、Agent 或前端页面。

## 先创建自己的仓库

推荐点击仓库首页的 **Use this template**。这样会得到一份没有原提交历史的新仓库，后续版本和 Issue 都由你自己维护。

也可以直接 Fork。如果准备长期维护自己的分支，建议在 GitHub 设置里修改仓库名称、简介和社交预览图。

```bash
git clone https://github.com/你的用户名/你的仓库名.git
cd 你的仓库名

python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,api,data]'

cd frontend
npm ci
```

## 五分钟换成自己的品牌

| 想改什么 | 修改位置 |
| --- | --- |
| 页面名称、短标题、首屏文案 | `frontend/src/branding.ts` |
| 浏览器标签名称和页面描述 | `frontend/index.html` |
| GitHub 首页横幅 | `docs/assets/hero.svg` |
| 项目介绍和截图 | `README.md`、`docs/assets/dashboard.png` |
| Python 包名、说明和版本 | `pyproject.toml`、`src/trading_agent/__init__.py` |
| 前端包名和版本 | `frontend/package.json` |

页面品牌文案集中在一个文件里。一般只需要先修改下面几项：

```ts
export const appBrand = {
  mark: "Q",
  category: "A 股短线研究",
  productName: "量化收盘研究室",
  heroEyebrow: "每日收盘研究",
  heroLead: "从全市场，找到",
  heroEmphasis: "少数机会",
  heroDescription: "你的项目说明",
} as const;
```

## 调整自己的选股规则

无需改 Python 就能调整常用阈值：

- `configs/market_scanner.yaml`：价格、成交额、涨跌幅、板块范围和基础股票池。
- `configs/workflow.yaml`：完美十字、锤子线、风险阈值和最终关注数量。
- `configs/news.yaml`：巨潮、东方财富和 Tushare 新闻源。
- `configs/llm.yaml`：模型服务、模型名称、超时和输出长度。

每次修改形态阈值后，先运行测试，再用一份固定收盘快照对比命中数量。不要只看个别股票是否命中。

## 接入新的行情数据源

1. 在 `src/trading_agent/providers/` 新建适配器，实现 `MarketDataProvider`。
2. 如果数据源还能提供历史行情和研究信息，再实现 `CandidateResearchProvider`。
3. 在 `src/trading_agent/bootstrap.py` 的注册表中加入新适配器。
4. 在 `tests/` 添加正常响应、字段缺失、分页中断和超时场景。
5. 密钥只能放在 `.env` 或部署环境变量中，不能写入前端或提交到 Git。

上层流程只读取标准领域模型，因此适配器内部可以使用 SDK、HTTP API 或本地数据库，不需要改动 Agent。

## 增加或替换 Agent

Agent 位于 `src/trading_agent/agents/`，工作流装配位于 `src/trading_agent/bootstrap.py`，执行顺序位于 `src/trading_agent/orchestrator/`。

新增 Agent 时请保持三个边界：

- 输入和输出使用 `domain/` 中的强类型对象。
- 外部请求统一放在 `providers/`、`news/` 或 `llm/` 适配器中。
- 风险否决和最终排序必须保留可解释原因，不能只返回一个模型分数。

## 提交前检查

在项目根目录运行：

```bash
pytest
ruff check src tests

cd frontend
npm run build
```

还应确认以下内容：

- `.env`、行情快照、新闻缓存和本地数据库没有进入 Git。
- README 中的数据来源、算法定义和截图与当前代码一致。
- 新增接口有失败降级策略，不会因为单一免费源中断而生成错误推荐。
- 版本号同时更新 Python 包、前端包和 `CHANGELOG.md`。

## 推荐的改版顺序

先修改品牌与默认参数，跑通固定快照；再替换数据源；最后增加新的 Agent 和学习逻辑。每次只改一层，出现偏差时更容易定位原因。
