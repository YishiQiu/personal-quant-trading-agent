# 参与贡献

感谢你愿意改进 Personal Quant Trading Agent。这个项目优先接受可验证、可配置并且不模糊数据边界的改动。

## 开发环境

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,api,data]'

cd frontend
npm ci
```

## 提交改动前

1. 从最新 `main` 创建分支。
2. 数据源必须通过现有 Provider 接口接入，不要把凭据写进代码或配置样例。
3. 改动筛选规则时，同时补充边界测试，并在文档中解释数学定义。
4. 新闻和模型输出必须能追溯到来源；不允许伪造链接、时间或确定性结论。
5. 保持 LLM 位于候选池之后，禁止让模型扫描整个市场。

运行检查：

```bash
pytest
ruff check src tests

cd frontend
npm run build
```

## 合并请求

请在 PR 中说明问题、实现方式、验证结果和可能影响的数据边界。界面变化建议附截图，数据 Provider 变化建议附一份脱敏后的字段样例。

提交代码即表示你同意按照项目的 MIT License 发布贡献内容。
