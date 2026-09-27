# KYC Review Agent PoC

由 RAG 支撑的 KYC/信贷材料初审辅助 Agent。当前实现包括 JSON 合成 Case、权限检查、
材料完整性与有效期检查、跨文档字段一致性检查、制度检索、结构化草稿生成、结果校验、
Runtime 以及 FastAPI 接口。

## 本地运行

```powershell
uv sync
uv run pytest
uv run uvicorn kyc_review_agent.api:app --reload
```

打开 API 文档：<http://127.0.0.1:8000/docs>

## 安全边界

- 只接受 `SYN-KYC-*` 或 `SYN-CR-*` 合成 Case；
- Agent 只生成审查建议；
- 不执行正式审批、客户通知或业务状态写入；
- 所有结果必须由 Auditor 确认。

## 当前数据流

```text
data/cases/*.json → CaseData → InMemoryCaseRepository
data/policies/*.json → PolicyRule → KycPolicyRepository
→ 按 Case 类型与审查日期选择生效制度
→ Case 归属权限检查
→ 材料完整性、有效期与跨文档一致性工具
→ 确定性或 OpenAI-compatible 草稿生成器
→ 引用与禁止性主张校验
→ ReviewResult
→ FastAPI
```

命名约定：

- `AuthorizationService` 管理“谁可以对哪个 Case 执行什么动作”；
- `KycPolicyRepository` 管理“KYC 业务应遵循哪一版制度”。

## 检索基础

`chunking.py` 将制度 Markdown 按二级标题切成可追溯的 `PolicyChunk`；
`retrieval.py` 在 `allowed_document_ids` 范围内执行可解释的本地词项检索并返回
Top-k。当前实现用于验证权限过滤、相关性排序和引用链路，后续可以替换为
Embedding 与向量索引。

启动时，`ingestion.py` 读取 `data/policies/*.md` 并构建 Retriever。运行时先由
`KycPolicyRepository` 选择当前有效制度，再将其 `document_id` 作为检索允许范围；
如果找不到有效制度或相关证据，任务会进入 `manual_review_required`。

## 审查草稿与引用验证

`generation.py` 定义可替换的 `ReviewDraftGenerator` 接口；当前使用确定性模板生成
结构化 `ReviewResult`，未来可以替换为 LLM 实现。`citation_validation.py` 会验证：

- 所有制度引用必须来自本次 Retriever 返回的 Chunk；
- 所有 Case 事实引用必须属于当前 `case_id`；
- 正常审查结果不能缺少制度引用。

验证失败的草稿不会直接返回，而会安全降级为 `manual_review_required`。

## 可选 LLM 草稿生成器

默认配置不访问外部模型，仍使用确定性模板。若要连接兼容 OpenAI Chat Completions
协议且支持 JSON mode 的模型网关，可在启动服务前设置：

```powershell
$env:KYC_DRAFT_GENERATOR = "openai_compatible"
$env:KYC_LLM_BASE_URL = "https://your-model-gateway.example/v1"
$env:KYC_LLM_API_KEY = "replace-with-a-secret"
$env:KYC_LLM_MODEL = "your-model-deployment"
uv run uvicorn kyc_review_agent.api:app --reload
```

模型只基于确定性工具结果和已检索证据撰写建议与限制说明。`status`、缺失材料、字段
冲突、制度引用和 Case 事实引用均由应用确定性生成；模型无权覆盖这些字段。模型文字
仍须通过禁止性主张校验，完整结果还须通过引用校验，且
`requires_auditor_decision` 始终由应用强制设置为 `true`。

结构化制度规则的 `source_ref` 必须与本次检索到的制度 Chunk 精确匹配，避免使用“虽被
检索到但不支持当前规则”的证据。任何模型或校验失败都会降级到人工审查，同时保留已经
确定的缺失材料、字段冲突、有效期限制和真实制度引用。

模型调用失败时，API 会安全降级到 `manual_review_required`。Uvicorn 日志只记录用于
排障的 `category`、HTTP 状态码、OpenAI error code 和 request ID，不记录 API Key、
完整 Prompt 或客户材料。可依据日志区分上游 HTTP 错误、网络错误和输出契约错误。

## RAG 离线评估

`data/evaluation/retrieval-cases.json` 保存带标准答案的检索问题。运行以下命令可计算
逐 Case 及汇总的 `Precision@K`、`Recall@K`：

```powershell
uv run python scripts/run-retrieval-eval.py --top-k 1
```

计算方式：

```text
Precision@K = Top-K 中相关 Chunk 数 / K
Recall@K = Top-K 中相关 Chunk 数 / 标准答案相关 Chunk 总数
```

报告同时提供 micro 与 macro 指标。当前评估只运行本地 Retriever，不调用 GPT‑5.5，
因此不会产生模型费用。增加制度或检索场景时，应同步扩充评估 Case，而不是只针对现有
三个样例调参。

## 五个 PoC 演示 Case

以下命令以不调用外部模型的确定性模式运行五个可重复演示场景：

```powershell
uv run python scripts/run-demo-cases.py
```

覆盖范围：

1. `SYN-KYC-101`：材料完整，可进入人工审查；
2. `SYN-KYC-102`：缺少地址证明；
3. `SYN-KYC-103`：地址证明过期；
4. `SYN-KYC-104`：公司注册号跨文档冲突；
5. `SYN-KYC-105`：注入可重复的 LLM 失败并验证安全降级。

若已配置 GPT‑5.5，可让前四个场景使用真实模型撰写建议；第五个场景仍使用受控故障注入：

```powershell
uv run python scripts/run-demo-cases.py --live-llm
```

报告中的 `passed` 和 `pass_rate` 根据预期业务结果计算。故障注入只存在于演示运行器，
不会暴露为 FastAPI 端点，也不会影响正常 Runtime。
