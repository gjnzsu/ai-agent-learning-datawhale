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
data/cases/*.json
→ Pydantic CaseData 契约校验
→ InMemoryCaseRepository
→ Case 归属权限检查
→ 材料完整性工具
→ ReviewResult
→ FastAPI
```
