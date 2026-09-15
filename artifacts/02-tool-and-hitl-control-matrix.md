# Artifact 02：Tool 与 Human-in-the-loop 控制矩阵

## 文档信息

- Status：Draft v0.1
- Owner：AI Platform Product / Delivery
- Purpose：定义 Agent 工具的权限、副作用、人工审批、失败处理和审计要求
- Decision stage：Tool onboarding / PoC design / Risk review
- Source lessons：
  - [第二周第一课：ReAct 与受控工具调用](../week02/lesson01-react-and-controlled-tools.md)
  - [第二周第三课：Human-in-the-loop 与执行治理](../week02/lesson03-human-in-the-loop-execution-governance.md)
  - [第四周第三课：MCP、A2A、ANP 与身份传递](../week04/lesson03-protocols-and-identity-propagation.md)
- Planned Week 5 update：补充工具调用评估、攻击测试、Hard Gate 和监控阈值
- Last updated：2026-09-14

## 1. Purpose

本 Artifact 把“Agent 可以使用某个工具”拆成可治理的执行契约。工具 Schema 只说明如何调用，并不代表调用者有权执行。

每次工具调用都应同时满足：

```text
有效权限
= 用户权限
∩ 应用权限
∩ Agent 权限
∩ 工具策略
∩ 数据策略
∩ 当前任务目的
```

控制目标是确保：

- 模型只看到当前任务允许的工具；
- 每次具体调用都执行资源级授权；
- 高风险动作在执行前获得人工确认；
- 重试不会造成重复副作用；
- 失败能够安全停止、降级或转人工；
- 全链路可审计但不泄漏凭证和敏感正文。

## 2. 工具风险分级

| 等级 | 工具类型 | 典型影响 | 默认策略 |
|---|---|---|---|
| T0 | 本地确定性计算 | 不访问敏感系统，不产生外部副作用 | 自动执行 |
| T1 | 低敏只读查询 | 读取批准的公共或内部低敏数据 | 授权后自动执行 |
| T2 | 敏感只读查询 | 客户、Case、账户或交易信息 | 资源级授权、字段最小化 |
| T3 | 可撤销写操作 | 创建草稿、工单或通知准备 | 执行前确认、幂等控制 |
| T4 | 高影响或不可逆操作 | 状态变更、客户通知、资金相关动作 | 默认禁止 Agent 直接执行 |

工具风险不是只看 HTTP Method。一个读取全量客户资料的 GET 操作，风险可能高于创建内部草稿的 POST 操作。

## 3. KYC Agent 工具控制矩阵

| Tool | Action | Risk | Agent mode | Human control | Authorization | Failure handling |
|---|---|---:|---|---|---|---|
| `search_policy` | 检索 KYC 制度 | T1 | 自动 | 结果后抽样 | 用户部门、密级、版本过滤 | 无结果时说明限制并转人工 |
| `get_case_documents` | 读取 Case 材料 | T2 | 受控执行 | 无需逐次审批 | 用户与 Case 绑定、字段范围 | 拒绝越权，不降级到共享账号 |
| `get_aml_report` | 查询 AML 报告 | T2 | 受控执行 | 高敏结果可复核 | 用户、应用、Agent、Case、用途交集 | 超时有限重试，失败后转人工 |
| `extract_document_fields` | 提取材料字段 | T1 | 自动 | 低置信度复核 | 只处理当前任务文件 | 标记置信度，不猜测缺失值 |
| `compare_case_information` | 比较数据矛盾 | T0/T1 | 自动 | 结果后复核 | 仅使用已授权上下文 | 返回冲突字段和证据 |
| `draft_review_summary` | 生成审核建议 | T1 | 自动生成 | 必须由 Auditor 复核 | 不得输出未授权字段 | 证据不足时标记不确定 |
| `create_follow_up_task` | 创建补件草稿 | T3 | 审批后执行 | 行动前确认 | 限定 Case、任务类型、接收方 | 幂等键，失败时查询状态 |
| `send_customer_notification` | 向客户发送通知 | T4 | 禁止首期直接执行 | 必须人工确认 | 正式通知服务再次授权 | 不自动重试，防止重复发送 |
| `update_case_status` | 修改正式 Case 状态 | T4 | Agent 不直接执行 | 必须由业务流程批准 | System of Record 自身授权 | 返回明确失败，不绕过流程 |
| `approve_kyc_case` | 最终审批 | T4 | 禁止 | 业务责任人决定 | 正式审批系统控制 | Agent 仅提供建议 |

## 4. Human-in-the-loop 控制点

### 4.1 Action before：执行前审批

适合：

- 对外发送通知；
- 创建或修改正式业务记录；
- 涉及客户权益或监管义务的动作；
- 可能产生不可逆副作用的工具；
- Agent 置信度或证据质量低于门槛。

审批界面至少显示：

- Agent 建议执行什么；
- 目标客户、Case 或资源；
- 工具名称和关键参数；
- 使用的证据和数据版本；
- 预计影响与可撤销性；
- 风险提示；
- Approve、Reject 和 Edit 选项。

审批时要锁定具体 Action，而不是让用户笼统同意“后续所有操作”。

### 4.2 In execution：执行中接管

触发条件示例：

- 工具连续失败或超时；
- 检索结果互相矛盾；
- 任务超过最大步数、时间或成本；
- 权限被拒绝；
- Agent 请求使用未批准工具；
- 子 Agent 委派超过最大深度；
- 无法判断操作是否产生副作用。

### 4.3 Result after：结果后复核

适合：

- 风险提示和案例摘要；
- 制度解释；
- 需要专业判断的建议；
- 最终交付给客户或监管方的内容。

结果后复核不能用于补救本应在执行前阻止的高风险动作。

## 5. 两阶段授权

### 阶段一：能力暴露前过滤

在模型选择工具前，根据用户、应用、任务和环境筛选允许的工具集合。目标是避免模型看到不应使用的能力。

### 阶段二：具体调用授权

当模型已经生成工具和参数后，再检查：

- 用户是否能访问目标 Case；
- 应用和 Agent 是否获准使用该工具；
- Scope、Audience 和 Purpose 是否匹配；
- 数据字段和时间范围是否必要；
- 参数是否通过 Schema 和业务规则；
- 是否需要人工批准。

两阶段授权不能互相替代。

## 6. 身份与凭证控制

一条调用链至少区分：

| Identity | Example | Control purpose |
|---|---|---|
| End user | KYC Auditor | 决定可访问哪些 Case 和字段 |
| Client application | KYC Copilot Web | 识别请求来自哪个应用 |
| Agent workload | `kyc-agent-prod-v1` | 限制哪个 Agent 版本可调用工具 |
| Downstream service | AML API | 将凭证绑定到目标 Audience |

凭证要求：

- 使用短期、下游专用令牌；
- Scope 只包含本次需要的操作；
- Audience 绑定目标服务；
- 可绑定 Case、字段范围和用途；
- 每一跳重新授权；
- 不将原始 Bearer Token 放入 Prompt、Memory、普通日志或工具结果。

## 7. 参数、执行与结果控制

### 7.1 调用前

- 工具来自批准的注册中心；
- 工具版本与 Schema 已锁定；
- 参数通过类型、枚举、长度和业务规则校验；
- 客户、Case、金额、时间范围等关键值不能仅依赖自由文本；
- 高风险 Action 已获得具体审批；
- 生成 `task_id`、`trace_id` 和 `action_id`。

### 7.2 执行中

- 设置连接和执行超时；
- 限制调用次数、并发、总步骤和总 Token；
- 只对安全且明确可重试的操作重试；
- 写操作使用 `idempotency_key`；
- 调用方和下游同时执行授权；
- 支持取消、熔断和人工接管。

### 7.3 结果后

- 将工具结果视为外部不可信输入；
- 验证结果 Schema、类型和大小；
- 做字段最小化、脱敏和数据分级检查；
- 防止工具结果中的 Prompt Injection 被当成系统指令；
- 将正式状态保存在 System of Record，而不是 Agent Memory；
- 记录结果状态与摘要，不保存无必要的敏感正文。

## 8. 失败处理矩阵

| Failure | Retry | Fallback | Human action | Prohibited response |
|---|---:|---|---|---|
| 参数 Schema 失败 | 否或仅修正一次 | 请求补充输入 | 必要时接管 | 猜测客户 ID |
| Authorization denied | 否 | 无 | 说明无权访问 | 改用共享高权限账号 |
| Read tool timeout | 有限次数 | 使用已批准缓存并标注时间 | 需要时接管 | 无限循环调用 |
| Write action 状态不明 | 否，先查状态 | 进入 pending/manual | 人工核对 | 直接重复提交 |
| RAG 无有效来源 | 可改写查询一次 | 返回“证据不足” | 专业人员处理 | 编造制度答案 |
| Tool output validation 失败 | 否 | 丢弃不可信结果 | 调查工具版本 | 把原始输出交给模型 |
| Budget/step limit reached | 否 | 保存进度 | 人工决定继续或终止 | 绕过预算限制 |
| Downstream partial success | 依业务契约 | 补偿或人工恢复 | 业务 Owner 处理 | 声称全部成功 |

## 9. 审计事件

建议记录以下结构化字段：

| Category | Fields |
|---|---|
| Subject | user_id、application_id、agent_id、agent_version |
| Task | task_id、parent_task_id、trace_id、delegation_id |
| Authorization | policy_version、decision、scope、purpose |
| Tool call | server_id、tool_name、tool_version、action_id |
| Resource | case_id、data_classification、field_scope |
| Execution | start/end time、status、latency、retry_count |
| Result | result_schema_version、artifact_hash、error_code |
| HITL | approver_id、decision、time、edited_fields |
| Cost | model、input_tokens、output_tokens、estimated_cost |

禁止记录：

- Access Token、Refresh Token、密码和 API Key；
- 完整模型内部思维过程；
- 与审计目的无关的客户敏感正文；
- 未脱敏的工具输入输出副本。

## 10. Tool onboarding checklist

- [ ] 工具有明确 Owner、用途和支持团队。
- [ ] 读写属性、业务副作用和风险等级已确认。
- [ ] 输入输出 Schema 和错误契约已版本化。
- [ ] 允许的用户、应用、Agent 和环境已定义。
- [ ] 数据、资源和字段级权限已定义。
- [ ] 超时、重试、幂等和补偿策略已定义。
- [ ] HITL 类型和审批责任人已定义。
- [ ] 结果过滤、脱敏和 Prompt Injection 控制已定义。
- [ ] 审计、指标、告警和追踪字段已定义。
- [ ] 工具禁用、版本回退和紧急接管机制已验证。

## 11. Key decisions

1. Tool Schema 不作为授权依据。
2. 只读工具也需要根据数据敏感度分级。
3. 模型不直接控制最终授权决定。
4. KYC PoC 默认只允许 T0–T2 工具。
5. T3 工具必须执行前审批并具备幂等性。
6. T4 工具不纳入首期 Agent 直接执行范围。
7. Agent 的建议、审批和正式执行分别由不同责任层处理。
8. 安全拒绝不能通过降级到高权限共享账号绕过。

## 12. Future updates

完成 Week 5 后补充：

- Tool selection accuracy 与 parameter accuracy；
- 未授权调用、审批绕过和跨 Case 访问 Hard Gate；
- Prompt Injection 与 malicious tool output 测试；
- P95 latency、timeout 和 retry 告警阈值；
- 人工接管率、审批通过率和修改率；
- Tool/MCP Server 版本回归测试要求。
