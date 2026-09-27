# KYC Review Agent PoC

由 RAG 支撑的 KYC/信贷材料初审辅助 Agent。当前阶段先实现不依赖真实 LLM
和生产系统的确定性基础，包括 JSON 合成 Case、权限检查、材料完整性检查、Runtime
以及 FastAPI 接口。

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
→ 材料完整性工具
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
