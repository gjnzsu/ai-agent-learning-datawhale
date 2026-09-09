# 第三周 · 第三课：框架选型与 Java/Python 集成

> 适合角色：银行 AI 平台项目经理；建议用时：110～140 分钟。前置知识：平台分层、受控执行、可靠性、发布和可观测性。本课重点：在业务约束下选择 Agent 实现方式，并为 Java 业务系统与 Python Agent 服务设计稳定边界。

> 学习状态：**待学习**。完成讲义阅读和三项练习后，再更新为已完成。

## 资料来源与改编说明

本课以 Datawhale Hello-Agents [第六章《框架开发实践》](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter6/%E7%AC%AC%E5%85%AD%E7%AB%A0%20%E6%A1%86%E6%9E%B6%E5%BC%80%E5%8F%91%E5%AE%9E%E8%B7%B5.md)对 AutoGen、AgentScope、CAMEL 和 LangGraph 的对比，以及[第七章《构建你的 Agent 框架》](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter7/%E7%AC%AC%E4%B8%83%E7%AB%A0%20%E6%9E%84%E5%BB%BA%E4%BD%A0%E7%9A%84Agent%E6%A1%86%E6%9E%B6.md)的统一模型、消息、配置、Agent 和工具接口为主线。

同时参考：

- [LangGraph 官方概览](https://docs.langchain.com/oss/python/langgraph/overview)：状态化编排、持久执行、流式输出和 Human-in-the-loop。
- [AutoGen Agent Runtime 官方文档](https://microsoft.github.io/autogen/stable/user-guide/core-user-guide/core-concepts/architecture.html)：独立与分布式 Runtime、消息和 Agent 生命周期。

框架功能与成熟度会持续变化。本课不作永久性的产品排名，而是建立可重复使用的选型方法；正式决策时应使用当时版本完成 PoC、安全评审和运维验证。

## 一、本课目标

完成本课后，你应该能够：

1. 从协作模式、控制方式和工程需求比较 Agent 框架。
2. 解释为什么银行高风险流程通常需要显式控制。
3. 区分框架能力、企业平台能力和业务应用能力。
4. 使用 Build vs Buy 维度比较自研、开源框架和低代码平台。
5. 设计 Java 业务系统与 Python Agent 服务的同步和异步接口。
6. 定义身份透传、契约版本、幂等、错误处理和降级边界。

## 二、先选问题，不要先选框架

错误起点：

```text
我们要使用某个热门 Agent 框架，可以做什么项目？
```

更合理的起点：

```text
业务任务需要多少动态决策？
流程是否必须可预测、可审计？
是否真的需要多个 Agent？
是否包含高风险工具？
任务是短请求还是长任务？
需要怎样的暂停、恢复和人工介入？
团队能维护多复杂的技术栈？
```

如果业务步骤完全固定，普通 Workflow 或 Java 服务可能已经足够，不必为了使用框架而引入 Agent。

## 三、两个设计方向：显式控制与涌现式协作

### 显式控制

开发者明确节点、边、条件和停止状态：

```text
材料检查
→ 风险分析
→ 合规规则
→ 人工复核
→ 正式决定
```

优势：

- 路径和控制点清晰。
- 易于设置权限、预算和审计。
- 容易重放和定位故障。

局限：

- 开发者需要提前设计状态和分支。
- 开放探索能力受到约束。

### 涌现式协作

开发者定义多个角色、目标和通信规则，由 Agent 通过对话决定协作过程：

```text
研究 Agent ↔ 数据 Agent ↔ 报告 Agent ↔ Reviewer Agent
```

优势：

- 适合探索、讨论和开放任务。
- 角色扩展灵活。

局限：

- 路径可能不稳定。
- 容易偏题、循环和增加成本。
- 权限与责任边界更难证明。

银行场景不是一律禁止涌现式协作，而是通常让它运行在受控节点内部：

```text
外层确定性状态图控制阶段和权限
内层允许多个 Agent 讨论或分析
输出经过规则和人工复核后才能进入下一阶段
```

## 四、LangGraph 的定位

核心思路：把 Agent 或长任务建模为状态图。

适合：

- 需要明确节点、条件分支和循环。
- 需要持久化状态、暂停恢复和 HITL。
- 需要精确控制高风险工具调用。
- 需要对每个阶段进行监控和审计。

需要注意：

- 图结构仍需团队自行设计。
- 模型网关、企业权限、审计和发布平台通常需要另行建设或集成。
- 复杂图可能出现状态定义膨胀和维护困难。

对 KYC 审查这类有明确阶段和人工复核的任务，状态图通常是较自然的表达方式，但最终仍需 PoC 验证。

## 五、AutoGen 的定位

核心思路：用可对话 Agent、消息和 Runtime 组织多 Agent 协作。

适合：

- 多角色讨论和协作。
- 研究、代码生成、分析和 Reviewer 循环。
- 需要事件驱动或分布式 Agent Runtime 的场景。

需要注意：

- 对话式协作可能偏题、循环或难以复现。
- 必须显式设置终止条件、消息预算和工具权限。
- 高风险业务阶段仍需要外部 Workflow、Policy 和 HITL 控制。

如果 KYC 场景只是需要“数据分析 Agent 与报告 Agent 讨论”，可以在一个受控分析节点内尝试；不宜让群聊直接决定正式 KYC 结果。

## 六、AgentScope 的定位

Datawhale 将 AgentScope 描述为工程化优先的多 Agent 平台，强调消息、Pipeline、运行时、分布式和可观测能力。

适合重点考察：

- 消息驱动的多 Agent 协作。
- Agent 生命周期和分布式部署。
- 并发任务与工程化运行能力。
- 希望获得较完整开发工具链的团队。

需要注意：

- 验证与银行现有基础设施、身份体系和监控体系的兼容性。
- 验证版本成熟度、升级路径、社区和商业支持。
- 消息驱动会引入重复、乱序、最终一致性等工程问题。
- 框架内置能力不能替代银行自身的权限和合规控制。

## 七、CAMEL 在本路线中的位置

CAMEL 强调角色扮演和多 Agent 协作研究，适合开放式角色协作和实验。

对于银行 AI 平台项目经理，本阶段的学习重点不是掌握其 API，而是理解：

- 角色提示可以促进专业分工。
- 多 Agent 对话不天然提高事实正确性。
- 高自主协作会增加成本、循环和责任边界问题。
- 生产选型仍需验证状态、权限、恢复和运维能力。

## 八、框架对比不是简单打分

| 维度 | LangGraph | AutoGen | AgentScope |
| --- | --- | --- | --- |
| 主要抽象 | 状态图和节点 | Agent、消息与对话 | Agent、消息、Pipeline 与 Runtime |
| 控制方式 | 偏显式 | 偏协作涌现，可增加控制 | 消息驱动与工程化编排 |
| 典型优势 | 状态、分支、循环、HITL | 多角色协作 | 多 Agent 工程化与分布式能力 |
| 典型风险 | 图和状态复杂度 | 对话漂移与循环 | 基础设施和消息复杂度 |
| 银行验证重点 | 恢复、权限节点、审计 | 终止、预算、隔离 | 一致性、部署、生态兼容 |

这只是架构理解，不是永久排名。需要用同一业务 Case、同一数据和同一验收指标做 PoC。

## 九、框架能力不等于平台能力

无论选择哪个框架，仍需确认是否具备或如何集成：

- 企业身份认证与细粒度授权。
- 模型网关、工具网关和密钥管理。
- Prompt、配置、工具和策略版本发布。
- 审计、防篡改和日志保留。
- 多租户、配额、成本分摊和数据隔离。
- 评测、灰度、回退和紧急停止。
- 运维 SLA、灾备和事件响应。

框架回答“Agent 逻辑怎样实现”，平台回答“组织怎样规模化运营并治理”。

## 十、Build vs Buy 的三类选择

### 基于开源框架自研平台

优势：

- 控制能力和扩展性高。
- 容易集成现有银行基础设施。
- 可以保持业务与供应商边界。

代价：

- 需要自行建设运行、治理、发布和运营能力。
- 对工程团队要求高。
- 需要持续跟踪框架升级和安全问题。

### 采购商业或低代码平台

优势：

- 上手快，常带有可视化编排和运营界面。
- 通用连接器和管理功能较完整。
- 厂商可能提供实施和支持。

代价：

- 深度定制和迁移可能困难。
- 需要评估数据边界、部署模式和供应商锁定。
- 高风险场景的控制深度未必满足要求。

### 自建轻量执行引擎

优势：

- 抽象较少，控制清晰。
- 对少量固定场景可能更简单。

代价：

- 容易重复实现状态、工具和可观测性。
- 长期维护成本可能被低估。
- 随场景增长容易演变成不完整的平台。

## 十一、Build vs Buy 决策维度

| 维度 | 关键问题 |
| --- | --- |
| 场景匹配 | 是否支持状态、HITL、长任务和受控工具？ |
| 安全合规 | 数据在哪里处理，权限和审计能否接入？ |
| 可控性 | 能否限制步骤、成本、模型和工具？ |
| 可运维性 | 是否支持监控、恢复、灰度和回退？ |
| 集成能力 | 是否兼容 Java、API、消息和现有网关？ |
| 可移植性 | Prompt、流程、数据和工具能否迁移？ |
| 成本 | 许可、算力、开发、运营和退出成本是多少？ |
| 生态 | 社区、版本节奏、人才和供应商支持如何？ |
| 交付速度 | 多久能达到 PoC 和生产验收？ |

不要只比较软件许可费。总拥有成本还包括开发、测试、运维、安全评审、培训、升级和迁移。

## 十二、建议的 PoC 方法

使用同一个 KYC 辅助任务比较候选方案：

```text
固定输入：同一组脱敏 Case
固定流程：材料检查 → AML 摘要 → 报告 → HITL
固定工具：相同 Mock 或沙箱接口
固定模型：尽量保持一致
固定指标：正确性、延迟、成本、恢复、审计和开发效率
```

除正常路径外，必须测试：

- AML 超时。
- 权限拒绝。
- 人工审批等待和恢复。
- 模型输出不符合 Schema。
- 工具结果不确定。
- Prompt 或 Agent 版本回退。

## 十三、Java 与 Python 的推荐边界

在多数现有银行系统中，可以采用：

```text
Java 业务系统
负责正式业务流程、业务状态、用户界面和交易一致性
        ↓ 稳定服务契约
Python Agent 服务
负责 Agent 编排、模型交互、分析和工具选择建议
```

两边不应共享 Python 框架内部对象，也不建议直接共享数据库表作为服务接口。

### Java 侧通常负责

- 正式 KYC Case 和业务规则入口。
- 用户身份、业务权限和操作界面。
- 发起、取消和查询 Agent 任务。
- 展示证据与人工审批。
- 根据授权结果调用正式业务能力。
- Agent 不可用时的业务降级。

### Python 侧通常负责

- Agent Runtime 和状态图。
- Prompt、上下文和模型交互。
- 分析工具编排。
- 生成结构化建议和证据引用。
- 保存 Agent 检查点和执行轨迹。
- 返回任务状态，而非自行成为 KYC 权威系统。

## 十四、同步、异步和流式接口

### 同步 HTTP

适合：

- 短时间内可完成的摘要或分类。
- 调用方必须立即获得结果。
- 超时和重试语义清晰。

不适合等待数分钟或数小时的长任务。

### 异步任务 API

适合：

- 多步骤 Agent。
- 需要工具、重试和人工审批。
- 调用方可以稍后查询结果。

```text
POST /agent-tasks → 返回 task_id
GET /agent-tasks/{task_id} → 查询状态
POST /agent-tasks/{task_id}/cancel → 取消
```

### 事件或回调

适合通知状态变化：

```text
TASK_COMPLETED
TASK_FAILED
TASK_WAITING_FOR_HUMAN
TASK_CANCELLED
```

事件需要考虑签名验证、重复投递、乱序、幂等消费和失败重放。

### 流式输出

适合显示生成进度或草稿，但流式文本不能被当成正式业务结果。最终结果仍需结构化完成事件和完整性校验。

## 十五、异步任务契约示例

### 创建任务

```http
POST /v1/agent-tasks
Authorization: Bearer <service-token>
Idempotency-Key: <request-id>
Content-Type: application/json
```

```json
{
  "agent_id": "kyc-review-assistant",
  "case_id": "KYC-2026-00128",
  "requested_by": "auditor-008",
  "goal": "生成带证据来源的 KYC 审查辅助摘要",
  "input_version": 7
}
```

```json
{
  "task_id": "TASK-1001",
  "status": "QUEUED",
  "agent_release": "kyc-agent-0.4.0",
  "submitted_at": "2026-09-09T10:00:00+08:00"
}
```

### 查询状态

```json
{
  "task_id": "TASK-1001",
  "case_id": "KYC-2026-00128",
  "status": "WAITING_FOR_HUMAN",
  "current_stage": "SUPPLEMENT_REVIEW",
  "result_version": 2,
  "updated_at": "2026-09-09T10:03:21+08:00"
}
```

接口不应暴露 LangGraph 节点对象或 Python 类名。外部契约应使用稳定的业务术语。

## 十六、身份与权限传递

需要同时区分：

- 最终用户身份：哪位 Auditor 发起任务。
- Java 应用身份：哪个业务应用调用 Agent 平台。
- Python 服务身份：Agent 服务调用哪个下游工具。

```text
用户登录凭证
→ Java 应用验证
→ 生成受限的任务授权上下文
→ Agent 平台验证应用与上下文
→ Tool Gateway 根据用户、应用、Case 和操作再次授权
```

不应把用户的长期凭证或数据库密码直接传给 LLM。下游服务也不能只因为请求来自 Agent 服务，就允许访问所有客户数据。

## 十七、接口版本与 Schema

接口契约需要定义：

- 必填字段、类型、长度和枚举。
- 请求与结果版本。
- 向后兼容策略。
- 未知字段处理方式。
- 错误码和是否可重试。
- 时间、时区、金额和精度格式。
- 敏感字段和日志规则。

结构化结果示例：

```json
{
  "status": "COMPLETED",
  "summary": "...",
  "evidence": [
    {
      "source_system": "KYC",
      "record_id": "DOC-901",
      "source_version": 4
    }
  ],
  "recommendation": "REQUEST_SUPPLEMENT",
  "requires_human_decision": true
}
```

模型自由文本应放在受控字段中，不能替代状态枚举和业务标识。

## 十八、错误处理契约

错误响应至少应区分：

```text
INVALID_REQUEST：输入不合法，不应原样重试
UNAUTHORIZED：身份无效
FORBIDDEN：没有该 Case 或操作权限
DEPENDENCY_UNAVAILABLE：依赖暂时不可用，可按策略重试
TASK_CONFLICT：Case 版本或并发冲突
POLICY_DENIED：行动被策略拒绝
HUMAN_REVIEW_REQUIRED：等待人工，不是技术失败
TASK_LIMIT_REACHED：达到步数、时间或成本上限
```

Java 调用方不能对所有 5xx 或超时无限重试，尤其要避免重复创建任务和重复外部行动。

## 十九、幂等、取消与并发

### 创建任务幂等

Java 使用 `Idempotency-Key` 防止请求超时后创建两个相同任务。

### 工具行动幂等

Python Runtime 使用 `action_id` 防止恢复后重复发送通知。

### 取消任务

取消是状态请求，不代表所有正在执行的外部操作能够瞬间撤回。响应应说明：

```text
CANCEL_REQUESTED
CANCELLED
TOO_LATE_TO_CANCEL
MANUAL_RECONCILIATION_REQUIRED
```

### 并发控制

提交时携带 `input_version`。如果 KYC Case 已被更新，旧任务在写入前应检测冲突，而不是覆盖新状态。

## 二十、降级边界

Python Agent 服务不可用时，Java 业务系统应提前定义：

- 是否可以继续传统人工 KYC 流程。
- 是否显示最近一次已确认结果。
- 哪些按钮和自动操作必须禁用。
- 正在等待审批的任务如何展示。
- 恢复后是否自动重放积压任务。

推荐原则：

```text
Agent 是增强能力，而不是让核心业务失去独立运行能力；
高风险流程降级时，应回到人工或确定性流程。
```

## 二十一、反模式

### Java 直接依赖 Python 框架对象

框架升级会破坏外部系统，应通过稳定 API 或事件 Schema 隔离。

### Java 与 Python 共享数据库表

双方直接写同一表会模糊数据所有权、事务和版本边界。服务应通过契约协作。

### Python Agent 直接修改正式业务数据库

会绕过业务校验、授权和审计。应调用受控业务 API 或工具网关。

### 一个 HTTP 请求等待整个人工审批流程

长连接容易超时且难恢复，应使用异步任务和状态查询。

### 把模型输出直接映射成业务状态

必须经过 Schema、规则、权限和人工控制，正式状态由权威业务系统保存。

### 双方都自动无限重试

Java、Runtime、网关和下游同时重试会造成重试风暴。应明确每层重试责任和总预算。

## 二十二、KYC 逻辑架构草图

```text
[KYC Java Application]
  ├─ 正式 Case、用户界面、人工决定
  └─ Agent Task Client
             │ REST / Events
             ▼
[Agent Platform API Gateway + IAM]
             ▼
[Python Agent Runtime]
  ├─ State Graph / Checkpoint
  ├─ Prompt & Release Config
  └─ Policy Decision Point
        │               │
        ▼               ▼
[Model Gateway]    [Tool Gateway]
                         ├─ KYC Adapter → KYC System
                         ├─ AML Adapter → AML System
                         └─ Notify Adapter → Notification System

横切能力：Audit、Trace、Metrics、Evaluation、Cost、Secrets
```

## 二十三、项目经理选型清单

### 框架

- 是固定 Workflow、单 Agent 还是多 Agent？
- 是否需要状态图、循环、暂停恢复和分布式消息？
- 终止、权限和成本是否可强制控制？
- 团队是否能调试和升级该框架？

### Build vs Buy

- 核心差异化能力是什么？
- 哪些能力可采购，哪些必须由银行控制？
- 数据、审计和退出机制是否可接受？
- 三年总拥有成本如何？

### Java/Python 集成

- 谁拥有正式业务状态？
- 接口是同步、异步、事件还是流式？
- 身份、权限和 Case 范围如何传递？
- 幂等、取消、并发和错误语义是否明确？
- Agent 不可用时业务如何降级？

## 二十四、本课学习方式

### 第一段：框架选型，约 40 分钟

阅读第二至第九节，理解显式控制、涌现协作及三种框架的定位。

### 第二段：Build vs Buy，约 25 分钟

阅读第十至十二节，建立企业级选型维度和 PoC 方法。

### 第三段：Java/Python 集成，约 45 分钟

阅读第十三至二十三节，理解服务边界、接口模式、身份、版本、错误和降级。

## 二十五、轻量练习

1. 为 KYC、研究报告协作和高并发客服三个场景分别选择一种编排方向，并说明控制重点。
2. 使用五个维度比较“开源框架自研”和“采购低代码平台”。
3. 为 Java KYC 系统调用 Python Agent 服务写出创建任务、查询状态和完成事件的最小字段清单。

## 二十六、本课验收标准

- [ ] 能解释显式控制与涌现式协作的差异。
- [ ] 能概括 LangGraph、AutoGen 和 AgentScope 的主要定位。
- [ ] 能说明框架为什么不等于企业 Agent 平台。
- [ ] 能使用统一维度执行 Build vs Buy 分析。
- [ ] 能设计公平的框架 PoC。
- [ ] 能划分 Java 业务系统与 Python Agent 服务职责。
- [ ] 能选择同步、异步、事件或流式集成方式。
- [ ] 能定义身份、Schema、错误、幂等、取消和降级边界。

完成本课后，将进入第四周：知识、记忆与上下文治理。
