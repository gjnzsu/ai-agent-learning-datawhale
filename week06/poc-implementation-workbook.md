# PoC 实践讲义：KYC/信贷材料初审辅助 Agent

> 状态：待实践  
> 建议投入：7～10 次实践，每次 60～120 分钟  
> 前置学习：已完成六周理论课程  
> 最终目标：交付一个使用公开制度、合成 Case、受控 RAG、只读校验工具和人工复核的可运行 PoC

---

## 一、这份讲义解决什么问题

前六周已经回答了“应该怎样设计”。PoC 阶段要回答另外四个问题：

1. 能否从干净环境启动？
2. 能否用固定 Case 重复得到可解释、可评估的结果？
3. 当检索、模型、工具或权限失败时，能否安全失败？
4. 能否用代码、测试、Trace 和报告证明以上结论？

这不是第四套理论设计。每一节都必须形成代码、测试或证据，并通过阶段 Gate 后再进入下一节。

---

## 二、PoC 目标与边界

### 2.1 目标用户

- KYC Auditor；
- 信贷材料初审人员；
- PoC 评审者。

### 2.2 核心任务

给定一个合成客户 Case 和审查目标，系统应：

1. 加载当前 Auditor 有权访问的合成 Case；
2. 检索当前有效的公开制度或合成材料规则；
3. 用确定性工具检查材料完整性和字段一致性；
4. 生成区分制度证据、Case 事实、推断和限制的审查草稿；
5. 对关键结论提供引用；
6. 在证据不足、材料冲突或高风险时转人工；
7. 保留可复现的 Release ID、Trace 和评估结果。

### 2.3 明确非目标

- 不使用真实客户数据；
- 不连接生产银行系统；
- 不自动批准、拒绝或修改正式 Case 状态；
- 不自动确定客户风险等级；
- 不向客户发送通知；
- 不把 LLM 当成权限、政策或客户事实来源；
- 不宣称 PoC 已经生产就绪。

---

## 三、完成后的最小演示

最终演示至少覆盖五条路径：

| 路径 | 输入 | 预期结果 |
|---|---|---|
| Normal | 材料齐全、字段一致 | 生成带引用草稿，等待 Auditor 确认 |
| Missing | 缺少地址证明 | 请求补充材料，不推断客户高风险 |
| Conflict | 两份材料的注册日期不一致 | 展示冲突并转人工 |
| Attack | 文档要求忽略规则并自动批准 | 不执行指令，记录安全结果 |
| Failure | 检索或模型超时 | 有限重试后安全转人工，不编造规则 |

演示时同时展示：

- API 请求与结构化响应；
- 引用和 Case 事实来源；
- Agent Trace；
- Release ID；
- 延迟、Token 和错误分类；
- 自动化测试与 Go/No-Go 结果。

---

## 四、目标目录

```text
projects/kyc-credit-review-agent/
├── data/
│   ├── knowledge/raw/
│   ├── knowledge/processed/
│   └── cases/
├── src/review_agent/
│   ├── contracts.py
│   ├── config.py
│   ├── ingestion.py
│   ├── chunking.py
│   ├── retrieval.py
│   ├── policy.py
│   ├── case_store.py
│   ├── tools.py
│   ├── review_pipeline.py
│   ├── citations.py
│   ├── tracing.py
│   └── api.py
├── tests/
│   ├── unit/
│   ├── component/
│   └── e2e/
├── evaluations/
│   ├── datasets/
│   ├── runners/
│   └── reports/
├── docs/
│   ├── architecture.md
│   ├── threat-model.md
│   ├── demo-script.md
│   └── pilot-roadmap.md
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

原则：业务代码、评估数据、文档和生成报告分开；测试答案不得进入检索索引。

---

## 五、实践路线与 Gate

| Milestone | 要完成的东西 | 进入下一阶段的 Gate |
|---|---|---|
| M0 | 项目骨架、边界、配置和 Release ID | 干净环境可以安装并运行空测试 |
| M1 | 合成 Case、知识文档和数据契约 | 数据校验测试全部通过 |
| M2 | Ingestion、Chunking 和 Retrieval | 固定查询能召回预期证据 |
| M3 | 只读工具、Review Pipeline 和 FastAPI | 三条核心业务路径端到端通过 |
| M4 | 评估集、安全测试和可观测性 | 无 Hard Gate，报告可关联 Release |
| M5 | Docker、演示和 Go/No-Go | 干净环境启动并完成五路径演示 |

不要同时开发所有组件。每个 Milestone 使用固定输入建立基线，再接入下一层。

---

## 六、M0：项目骨架与可重复环境

### 6.1 首版技术选择

PoC 建议保持简单：

- Python 3.11 或团队已验证版本；
- Pydantic：输入输出契约；
- FastAPI：服务入口；
- pytest：自动化测试；
- 本地向量索引或轻量向量库；
- HTTPX：外部模型或依赖调用；
- 标准 logging 或 OpenTelemetry：Trace 与 Metrics；
- Docker：可重复运行。

不要在第一版引入多 Agent、复杂 Workflow Engine、生产数据库和多个模型供应商。

### 6.2 配置分层

配置至少区分：

- 普通配置：Top-k、超时、Step Limit；
- 版本配置：模型、Prompt、Embedding、Index；
- 敏感配置：API Key、Token；
- 策略配置：允许集合、工具和业务边界。

密钥只通过环境变量或密钥服务注入，不能进入代码、镜像、日志和 Trace。

### 6.3 Release ID

首版 Release Bundle 至少记录：

```yaml
release_id: kyc-review-agent-0.1.0
agent_code: 0.1.0
model: configured-model
prompt: review-v1
document_snapshot: synthetic-rules-v1
chunking_config: section-500-50-v1
embedding_model: configured-embedding
index_version: index-v1
tool_schema: tools-v1
policy_bundle: policy-v1
evaluation_dataset: eval-v1
```

### M0 验收

- [ ] 项目目录已创建。
- [ ] 依赖可以从锁定文件安装。
- [ ] `.env.example` 不包含真实密钥。
- [ ] `pytest` 可以运行。
- [ ] `/health` 或最小程序可以启动。
- [ ] `/version` 能返回 Release ID。

---

## 七、M1：合成数据与契约

### 7.1 知识文档

准备 3～5 份公开或明确标记为合成的规则，覆盖：

- 个人 KYC 必需材料；
- 企业 KYC 必需材料；
- 地址证明有效期；
- 例外或补充材料；
- 规则版本变化。

每份文档至少保留：

```yaml
document_id:
title:
source_url:
publisher:
version:
effective_date:
classification: public_or_synthetic
content_hash:
```

### 7.2 合成 Case

准备 5～10 个 Case：

- 材料齐全；
- 缺少材料；
- 字段冲突；
- 文档过期；
- 证据不足；
- 越权访问；
- 文档 Prompt Injection。

示例：

```json
{
  "case_id": "SYN-KYC-001",
  "case_type": "kyc",
  "synthetic": true,
  "assigned_auditor": "auditor-demo",
  "submitted_documents": ["passport", "address_proof"],
  "extracted_fields": {
    "legal_name": "Example Person",
    "country": "XX"
  },
  "case_status": "draft"
}
```

### 7.3 Pydantic 契约

最低契约包括：

- KnowledgeDocument；
- Chunk；
- SyntheticCase；
- Citation；
- ReviewRequest；
- ReviewResult；
- StructuredError。

ReviewResult 必须明确区分：

```text
status
case_summary
missing_materials
conflicts
recommendation
citations
case_fact_refs
limitations
requires_auditor_decision
```

### M1 验收

- [ ] 所有 Case 都有 `synthetic: true`。
- [ ] Document、Chunk 和 Case ID 唯一。
- [ ] Chunk 可回溯到文档和章节。
- [ ] 知识事实与 Case 事实分开保存。
- [ ] 无真实姓名、账号、证件和交易数据。
- [ ] 无效数据会 fail fast，并返回结构化错误。

---

## 八、M2：先证明检索正确

### 8.1 实现顺序

```text
Parse
→ 按标题和段落切块
→ 过长段落二次切块
→ 元数据继承
→ Embedding
→ Index
→ Policy Filter
→ Top-k Retrieval
→ 有效期验证
→ 可选 Rerank
```

### 8.2 固定检索测试

至少定义五个查询，并提前写出预期 Chunk：

1. 个人 KYC 需要哪些身份证明？
2. 地址证明的有效期是多少？
3. 企业 Case 需要哪些注册材料？
4. 哪些情况需要额外材料？
5. 当前生效版本是什么？

先检查 Retrieval 是否找对证据，再接入 LLM。不要用生成 Prompt 掩盖检索错误。

### 8.3 检索断言

- 预期证据进入 Top-k；
- 失效版本不作为当前依据；
- 无权限集合不会被检索；
- 测试答案不在索引中；
- Chunk 保留来源、章节、版本和哈希；
- 相同索引版本可以重复构建。

### M2 验收

- [ ] 五个固定查询均保存预期证据。
- [ ] 报告 Recall@k 和错误 Case。
- [ ] 权限和有效期过滤有自动化测试。
- [ ] Index 版本进入 Release Bundle。
- [ ] 能区分“没有召回”和“召回后生成错误”。

---

## 九、M3：确定性工具、Agent Pipeline 与 API

### 9.1 先实现只读工具

至少实现两个确定性工具：

1. `check_required_materials`：比较制度要求与已提交材料；
2. `check_field_consistency`：比较多份材料中的关键字段。

工具必须具备：

- 明确 Schema；
- 输入校验；
- 只读边界；
- 用户与 Case 对象级授权；
- 超时；
- 结构化错误；
- 审计字段；
- 单元测试。

### 9.2 Pipeline 顺序

```text
Validate Request
→ Authenticate User
→ Authorize Case
→ Load Synthetic Case
→ Retrieve Authorized Evidence
→ Run Read-only Checks
→ Build Bounded Context
→ Generate Structured Draft
→ Validate Citations
→ Decide HITL Status
→ Return Response
```

LLM 只负责基于提供的证据组织草稿，不能：

- 提升权限；
- 修改 Case；
- 把缺失材料解释为客户高风险；
- 自动批准或拒绝；
- 使用未提供的制度常识补造结论。

### 9.3 API 契约

首版端点：

```text
POST /v1/review-tasks
GET  /v1/tasks/{task_id}
GET  /health
GET  /ready
GET  /version
```

不要把以下内容返回给调用方：

- API Key 或 Token；
- System Prompt；
- 完整私密推理过程；
- 未授权文档；
- 无必要的原始客户字段。

### 9.4 状态与错误

业务状态与 HTTP/技术状态分开：

| 情况 | 处理 |
|---|---|
| 请求格式错误 | HTTP 422 |
| 用户无权访问 Case | HTTP 403 |
| 材料缺失 | HTTP 200 + `more_information_required` |
| 证据冲突 | HTTP 200 + `manual_review_required` |
| 模型限流 | HTTP 429/503，有限重试 |
| 检索不可用 | HTTP 503 或安全降级 |
| 总截止时间超限 | HTTP 504 或转人工 |

### M3 验收

- [ ] Normal、Missing、Conflict 三条端到端路径通过。
- [ ] 越权 Case 返回 403，且没有泄漏 Case 是否存在。
- [ ] 工具超时不会无限重试。
- [ ] 引用不存在或不支持结论时转人工。
- [ ] 所有结果都要求 Auditor 最终确认。
- [ ] API 返回 request ID、task ID 和 Release ID。

---

## 十、M4：测试、评估、安全与可观测性

### 10.1 最小评估集

首版建议 12 条：

| 类型 | 数量 |
|---|---:|
| Normal | 3 |
| Missing / Boundary | 2 |
| Conflict / Unanswerable | 2 |
| Dependency Failure | 2 |
| Prompt Injection | 1 |
| Unauthorized Access | 1 |
| High-risk Request | 1 |

每条定义：

- 必须出现的事实；
- 禁止出现的结论；
- 预期证据；
- 允许的工具；
- 预期状态；
- 是否 Hard Gate；
- 评分方式。

### 10.2 分层评估

- Component：数据契约、Retriever、工具、Citation Validator；
- Trace：工具选择、参数、步骤、重试和授权决策；
- Result：正确性、完整性、Grounding 和拒答；
- End-to-end：用户目标是否完成；
- Security：注入、越权、泄漏、只读边界和资源耗尽。

### 10.3 Hard Gate

以下任一失败即 No-Go：

- 未授权 Case 或文档泄漏；
- Prompt Injection 导致危险动作；
- 凭证或敏感配置泄漏；
- 绕过只读工具边界；
- Agent 自动写入正式审批决定；
- 合成数据与真实客户数据边界被破坏；
- Trace 无法关联关键身份、版本和动作。

### 10.4 最小可观测性

Metrics：任务成功率、Recall@k、引用支持率、转人工率、P95、Token、成本、工具失败率。

Logs：请求状态、Policy 决策、工具结果、错误类别和版本变化；不得记录密钥或完整敏感载荷。

Traces：

```text
API
→ Policy
→ Case Load
→ Retrieval
→ Tools
→ Model
→ Citation Validation
→ HITL / Response
```

### M4 验收

- [ ] 12 条评估样本可重复执行。
- [ ] 检索和生成结果分开报告。
- [ ] Hard Gate 失败为零。
- [ ] 每次执行可关联完整 Release Bundle。
- [ ] 能从失败报告定位到 Trace 和组件。
- [ ] 报告延迟、Token、成本与人工接管。

---

## 十一、M5：Docker、演示与交付

### 11.1 Docker Gate

- 固定依赖版本；
- 使用非 root 用户；
- 不把密钥写入镜像；
- 暴露 Liveness 和 Readiness；
- 配置通过环境变量注入；
- 镜像关联 Release ID；
- 在干净环境启动并运行 Smoke Test。

### 11.2 演示材料

准备：

- 5～7 分钟演示脚本；
- 一页架构与数据流；
- 一页 Scorecard；
- 威胁模型与关键红队结果；
- Go/No-Go 决策；
- PoC 到 Pilot 的差距和 8～12 周路线图。

### 11.3 Go/No-Go

- **Go**：无 Hard Gate，核心路径与证据满足 PoC 门槛；
- **Conditional Go**：只有非关键缺陷，存在补偿控制、Owner 和期限；
- **No-Go**：出现 Hard Gate、关键证据缺失或无法安全停止。

### M5 验收

- [ ] Docker 从干净环境启动。
- [ ] `/health`、`/ready` 和 Smoke Test 通过。
- [ ] 五条演示路径可重复执行。
- [ ] README 能让另一位开发者独立运行。
- [ ] 评估报告与 Release ID 一致。
- [ ] 明确 PoC 不能直接进入生产的差距。

---

## 十二、建议实践节奏

| Session | 重点 | 当次必须提交的证据 |
|---|---|---|
| 1 | Scaffold 与 Release | 项目骨架、依赖、空测试、版本端点 |
| 2 | 数据与契约 | 合成文档、Case、Pydantic 测试 |
| 3 | Ingestion 与 Chunking | 可追溯 Chunk 和测试 |
| 4 | Retrieval | 固定查询、Recall@k 和错误分析 |
| 5 | Tools 与 Pipeline | 只读校验工具和三条核心路径 |
| 6 | FastAPI 与故障 | API、授权、超时和错误契约 |
| 7 | Evaluation 与 Security | 12 条评估集、红队和 Scorecard |
| 8 | Observability 与 Docker | Trace、指标、镜像和 Smoke Test |
| 9 | Demo 与 Go/No-Go | 演示脚本、报告和 Pilot 路线图 |

如果时间不足，优先完成 M0～M3 的可运行垂直切片，再增加评估与交付能力。

---

## 十三、每次实践的学习记录

每次提交建议记录：

```text
目标：本次只验证什么？
变更：新增或修改了哪些组件？
证据：哪些测试、Trace 或输出证明它有效？
问题：失败发生在哪一层？
决策：为什么选择当前实现？
风险：还有什么不能证明？
下一步：进入下一 Gate 前缺什么？
```

这能把 PoC 从“代码演示”提升为可复盘的工程学习成果。

---

## 十四、最终 Definition of Done

- [ ] 一个新环境可以按 README 启动服务。
- [ ] 全部数据均为公开或明确标记的合成数据。
- [ ] 检索结果可追溯到版本化文档与 Chunk。
- [ ] 材料完整性和字段一致性由确定性工具检查。
- [ ] 审查结果区分制度证据、Case 事实、推断和限制。
- [ ] Agent 不作出正式审批，关键路径进入 HITL。
- [ ] 正常、缺失、冲突、攻击和依赖失败路径可演示。
- [ ] 至少 12 条评估样本可重复运行。
- [ ] Security Hard Gate 失败为零。
- [ ] 请求可关联身份、Release Bundle 和 Trace。
- [ ] 报告质量、延迟、Token、成本和人工接管指标。
- [ ] Docker 从干净环境启动并通过健康检查。
- [ ] 完成 Go/No-Go 结论及 PoC 到 Pilot 差距清单。

完成这些条件后，PoC 才算从“学过”进入“做过并能证明”。

---

## 十五、第一步

从 Session 1 开始，只完成以下内容：

1. 创建项目目录；
2. 初始化依赖和测试；
3. 实现 `/health`、`/ready` 和 `/version`；
4. 定义 Release Bundle；
5. 运行第一条 Smoke Test。

此时不要连接模型、RAG 或真实外部服务。第一步的目标是建立一个可重复、可测试、可继续扩展的工程基线。
