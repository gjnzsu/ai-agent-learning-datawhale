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

模型只把确定性工具结果和已检索证据整理为结构化草稿。模型输出仍须通过引用校验和
禁止性主张校验，且 `requires_auditor_decision` 始终由应用强制设置为 `true`。
