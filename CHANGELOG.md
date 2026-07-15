# Changelog

本项目遵循 [Semantic Versioning](https://semver.org/)。

## [1.1.0] - 2026-07-15

面向中文开发者的可复刻项目模板版本，选股和评分逻辑保持不变。

### Added

- 新增集中管理页面名称、标记和首屏文案的 `frontend/src/branding.ts`。
- 新增完整的复刻与改版指南，覆盖品牌、策略、数据源、Agent 和发布检查。
- README 增加项目模板入口和更直观的三步改版说明。

### Changed

- 代码注释、模块说明、关键算法说明和配置注释统一改为自然中文。
- Python 包、FastAPI 和前端版本统一升级为 `1.1.0`。
- GitHub 首页横幅和版本说明更新为模板化版本。

### Verified

- Python 测试与 Ruff 静态检查通过。
- React / TypeScript 生产构建通过。
- SVG 横幅通过 XML 结构校验。

## [1.0.0] - 2026-07-15

首个稳定、可运行的个人 A 股尾盘研究版本。

### Added

- 全市场完整快照、完整性校验、失败保护与本地回放。
- 阳线完美十字、阳线锤子的严格数学门控，并明确排除 T 字线。
- 前端可配置价格上下限，以及创业板 `300/301`、科创板 `688/689` 开关。
- 同一筛选条件贯穿形态扫描、全市场审计和候选股深度研究。
- 候选股历史行情、量价趋势、新闻公告、风险指标与可选 DeepSeek 研究。
- FastAPI、React + TypeScript 研究工作台、SQLite 记录与 Markdown 报告。
- GitHub Actions、Dependabot、Issue / PR 模板、安全策略和 MIT License。

### Changed

- GitHub 首页改为视觉化、分层和可折叠的信息结构。
- 全市场界面使用中文说明具体排除原因，并显示本次实际应用的筛选条件。
- 前后端短暂版本不一致时保留筛选条件兜底，避免页面空白。

### Verified

- 34 项 Python 测试通过。
- Ruff 静态检查通过。
- React / TypeScript 生产构建通过。
- 使用 5,527 只股票快照完成自定义条件浏览器验收。

[1.1.0]: https://github.com/YishiQiu/personal-quant-trading-agent/compare/v1.0.0...v1.1.0
[1.0.0]: https://github.com/YishiQiu/personal-quant-trading-agent/releases/tag/v1.0.0
