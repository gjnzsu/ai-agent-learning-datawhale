# 第五周 · 第三课：Agent 上线准入、监控与运营闭环

> 状态：已完成（2026-09-19；正式准入演练延期至 PoC）
> 建议时长：90～120 分钟  
> 面向角色：银行 AI 平台项目经理、产品经理、架构师、开发、测试、SRE、安全、风险与业务运营人员  
> 本课目标：把离线评估和安全控制转化为可执行的上线决策、生产监控与持续改进机制

---

## 一、本课学习目标

完成本课后，你应该能够：

1. 解释为什么“评估通过”不等于“可以直接全量上线”。
2. 定义 Agent Release Candidate 的完整版本基线。
3. 设计从离线评估、UAT、Shadow、Canary 到受控生产的准入路径。
4. 把业务、质量、行为、安全、工程和人工采纳指标转化为 Release Gate。
5. 设计 Agent 的 Trace、Metric、Log 与在线抽样评估。
6. 区分降级、暂停、Kill Switch、回滚和补偿操作。
7. 建立告警、事件响应、反馈、评估集更新和版本改进的闭环。
8. 组织跨业务、技术、安全和风险团队完成 Go/No-Go 决策。

---

## 二、为什么 Agent 上线不是一次性动作

传统服务上线主要验证代码、接口、性能和基础设施。Agent 的行为还受到以下可变因素影响：

- 模型及其服务版本；
- System Prompt 与任务模板；
- RAG 数据、切分、Embedding、检索和重排；
- 工具描述、Schema、权限和下游返回；
- Agent 编排、记忆、停止条件和重试策略；
- Guardrail、审批与风险策略；
- 用户输入分布与真实业务环境。

因此，“同一应用版本”并不一定代表“同一 Agent 行为”。上线管理对象应是一个完整的 **Agent Release Bundle**，而不只是代码镜像。

> 上线准入回答“是否允许进入下一阶段”；生产运营回答“进入后如何发现偏差、限制影响并持续改进”。

---

## 三、Agent Release Bundle

每个 Release Candidate 至少要锁定以下版本：

| 组成部分 | 示例 | 为什么需要锁定 |
|---|---|---|
| Agent 代码 | runtime 1.3.0 | 决定状态机、路由和异常处理 |
| 模型 | provider/model/version | 模型升级可能改变输出与工具选择 |
| Prompt | system-prompt-v12 | Prompt 变化可能影响安全和质量 |
| RAG | corpus、chunk、embedding、reranker | 知识与检索变化会改变依据 |
| 工具 | MCP Server、schema、description | 工具定义变化可能改变调用行为 |
| 策略 | authorization、DLP、guardrail | 决定哪些行为被允许 |
| 记忆 | schema、namespace、TTL | 影响跨会话状态和隔离 |
| 评估集 | dataset-v3、rubric-v2 | 决定评估结果是否可比较 |
| 运行参数 | temperature、token、step limit | 影响稳定性、延迟与成本 |
| 基础设施 | image、region、quota | 影响可用性和数据边界 |

建议生成统一的 Release ID，并确保每条 Trace 都能关联到该版本组合。

```yaml
release_id: payment-investigation-agent-0.3.0
agent_code: 1.3.0
model: model-a-2026-08
prompt: system-v12
knowledge_snapshot: policy-2026-09-15
retrieval_config: retrieval-v5
tools: payment-query-mcp-2.1
policy_bundle: bank-agent-policy-v4
evaluation_dataset: eval-v3
```

如果无法还原某次执行使用的版本组合，就很难复现问题，也无法证明某个版本已经通过准入。

---

## 四、从开发到生产的分阶段路径

| 阶段 | 主要目标 | 数据与权限 | 退出条件 |
|---|---|---|---|
| Development | 验证基本流程 | 合成数据、Mock 工具 | 核心路径可运行 |
| Offline Evaluation | 验证质量与行为 | 固定评估集、隔离环境 | 指标达标，无 Hard Gate |
| Security / Red Team | 验证攻击与越权防线 | 测试身份、禁止生产写入 | 严重问题关闭并回归 |
| UAT | 验证业务适用性 | 脱敏或受控数据 | 业务 Owner 签署 |
| Shadow | 观察真实输入但不影响业务 | 只读、结果不展示或不执行 | 指标稳定、无重大未知风险 |
| Canary / Pilot | 小范围真实使用 | 最小权限、受限用户和限额 | 观察窗达标 |
| Controlled Production | 扩大范围 | 受控生产权限 | 持续监控与周期复审 |
| Full Rollout | 按批准范围推广 | 正式运营控制 | SLO、风险与采纳持续达标 |

### 4.1 Shadow 与 Canary 的区别

- **Shadow**：复制真实请求给候选版本，但候选结果不直接影响用户或业务。
- **Canary**：让少量真实用户或流量实际使用候选版本，并与稳定版本比较。
- **Pilot**：通常按业务范围选择少量团队、地区或场景，观察时间更长。
- **Blue-Green**：保留两套可切换环境，适合快速回退技术版本。
- **Feature Flag**：按用户、功能、工具或风险等级开启能力。

Agent 场景应优先按“用户 + 场景 + 工具权限”灰度，而不是只按随机流量比例。

---

## 五、上线准入不是单一平均分

### 5.1 六个准入维度

沿用第一课的评估框架：

1. Business Outcome；
2. Agent Behavior；
3. Answer Correctness；
4. Security and Compliance；
5. Engineering；
6. Human Adoption。

### 5.2 当前 PoC 基线

以下是前一课已经确定的初始门槛，适合作为 PoC 设计基线，不代表生产最终标准：

| 维度 | PoC 基线 | 说明 |
|---|---:|---|
| Business Outcome | ≥ 90% | 代表性任务成功率 |
| Agent Behavior | ≥ 80% | 工具选择、参数与轨迹符合预期 |
| Answer Correctness | ≥ 90% | 正确、完整且有依据 |
| Security and Compliance | ≥ 90% | 普通安全测试总体通过率 |
| Security Hard Gate | 0 次失败 | 越权、泄漏、审批绕过等零容忍 |
| Engineering Latency | P95 ≤ 15 秒 | 按端到端用户体验计算 |
| Average Cost | ≤ USD 0.10/任务 | 包括模型及主要工具成本 |
| Human Adoption | ≥ 80% | 建议被接受或愿意继续使用 |

关键原则：

- 指标必须基于足够且有代表性的样本；
- 总体通过率不能掩盖高风险分组失败；
- Hard Gate 失败时，其他指标再高也不能上线；
- PoC、Pilot 和 Production 可以使用不同门槛，但任何放宽都要记录批准人和期限；
- 指标定义、样本和计算方法必须版本化。

### 5.3 Release Gate 结构

| Gate | 示例 | 决策方式 |
|---|---|---|
| Hard Gate | 未授权访问、敏感数据泄漏、审批绕过 | 任一失败即 No-Go |
| Threshold Gate | 正确率、延迟、成本、采纳率 | 达到门槛才进入下一阶段 |
| Evidence Gate | UAT 签署、红队报告、回滚演练 | 缺证据即不能放行 |
| Conditional Gate | 已知中风险问题有补偿控制 | 风险 Owner 限期接受 |

---

## 六、Go/No-Go 决策包

上线会议不应只展示 Dashboard 截图。一个可审计的决策包至少包含：

1. 业务场景、目标用户和批准范围；
2. Release Bundle 与变更清单；
3. 离线评估结果及与基线版本的对比；
4. 红队结果、Hard Gate 和剩余风险；
5. UAT、数据、隐私和合规签署；
6. 容量、性能、成本与配额验证；
7. Canary 范围、观察窗口和成功指标；
8. 告警、Runbook、值班与升级路径；
9. Kill Switch、降级与回滚演练证据；
10. Go、Conditional Go 或 No-Go 的决策与责任人。

| 决策 | 含义 |
|---|---|
| Go | 所有强制条件满足，可按批准范围发布 |
| Conditional Go | 不涉及 Hard Gate；有补偿控制、Owner、期限和复审日期 |
| No-Go | Hard Gate 失败、关键证据缺失或无法控制影响 |

“Conditional Go”不能用来接受越权、客户数据泄漏或无法回滚等严重问题。

---

## 七、Agent 可观测性：不只监控基础设施

| 层级 | 要观察的问题 |
|---|---|
| Infrastructure | CPU、Memory、网络、容器、队列和依赖是否健康 |
| Application | API 延迟、错误、重试、超时和吞吐是否正常 |
| Agent Behavior | 规划、检索、工具、循环、停止和人工接管是否合理 |
| Business / Risk | 任务是否成功，是否产生越权、损失或合规影响 |

只看服务 200 OK，无法判断 Agent 是否调用了错误工具或生成了错误结论。

### 7.1 Metrics、Logs 与 Traces

- **Metrics**：发现趋势、SLO 违约和异常，例如 P95、失败率、Token 和成本。
- **Logs**：记录策略拒绝、审批结果、版本变更和错误等离散事件。
- **Traces**：还原一次任务跨模型、RAG、工具、Agent 和审批的完整路径。

三类信号应共享 trace ID、request ID 和 Release ID。

### 7.2 最小 Trace 字段

| 类别 | 建议字段 |
|---|---|
| 身份 | user、agent、tenant、delegation chain |
| 版本 | release、model、prompt、RAG、tool、policy |
| 输入 | intent、risk class、data classification；敏感载荷默认不明文记录 |
| 检索 | query、source IDs、scores、权限过滤结果 |
| 模型 | latency、token、finish reason、policy result |
| 工具 | tool、参数摘要、authorization result、latency、result status |
| 审批 | approver role、approval ID、parameter hash、decision |
| 结果 | task outcome、citations、fallback、human override |
| 成本 | model、retrieval、tool 与总任务成本 |
| 安全 | injection signal、DLP、denied action、Hard Gate |

> 可观测性不能以泄漏数据为代价。原始 Prompt、文档、工具响应和模型输出需要数据分级、脱敏、访问控制和留存期限。

---

## 八、线上指标看板

### 8.1 业务与采纳

- 任务成功率、平均处理时间和人工节省时间；
- 建议采纳率、人工覆盖率、用户满意度和投诉率。

### 8.2 答案与依据

- 在线抽样正确率、引用覆盖率和引用支持率；
- 无依据结论率、过期知识命中率和人工复核通过率。

### 8.3 Agent 行为

- 工具选择和参数正确率；
- 每任务平均步骤与工具调用数；
- 无效循环、重试、超时、非预期路径和人工接管率。

### 8.4 安全与合规

- 攻击尝试数与防御成功率；
- 实际越权、敏感数据泄漏和审批绕过事件；
- DLP 告警、策略拒绝与误拒率、红队回归通过率。

### 8.5 工程与成本

- 请求量、成功率、P50/P95/P99 延迟；
- 模型、RAG、工具和审批阶段耗时；
- 输入与输出 Token、单任务与单成功任务成本；
- 缓存命中、限流、可用性与错误预算消耗。

---

## 九、线上评估如何运行

建议组合四种方式：

1. **确定性实时检查**：权限、Schema、引用存在性、工具参数、DLP、限额。
2. **规则或模型抽样评估**：对一定比例的低风险任务做异步评分。
3. **人工质量抽检**：按风险、异常和随机样本分层抽样。
4. **业务结果回流**：将工单关闭、人工修改、客户投诉等结果与 Trace 关联。

### 9.1 抽样策略

- 高风险场景 100% 检查；
- 新版本与新用户群提高抽样率；
- 重点抽取低置信度、长轨迹、高成本任务；
- 重点抽取人工覆盖、投诉和异常结束任务；
- 保留随机基线样本，防止只看到已知问题。

### 9.2 LLM Judge 的线上边界

LLM Judge 可以扩大语义质量评估，但不应：

- 判断最终授权；
- 覆盖 Hard Gate；
- 自动批准高风险业务动作；
- 在没有人工校准时作为唯一上线依据。

Judge 的模型、Prompt、Rubric 和校准结果也要版本化。

---

## 十、Drift：生产环境为什么会逐渐偏离

| Drift 类型 | 示例 | 检测方法 |
|---|---|---|
| Input Drift | 用户开始提交新类型调查请求 | 意图与输入分布变化 |
| Knowledge Drift | 制度更新但知识库未刷新 | 来源时效、失效文档命中 |
| Retrieval Drift | 新文档改变 Top-K 结果 | 固定查询回归、引用变化 |
| Model Drift | 供应商升级模型 | Shadow 对比、黄金集回归 |
| Prompt Drift | 模板热更新未经过评估 | 配置版本审计 |
| Tool Drift | Schema、错误码或语义变化 | Contract Test、调用失败率 |
| Policy Drift | 权限和合规规则变化 | 策略版本与拒绝分布 |
| Business Drift | 工具被用于未批准场景 | 场景分类、用途审查 |

Drift 不一定代表系统变差，但意味着原来的评估证据可能不再充分。

---

## 十一、告警设计：从“有异常”走向“可行动”

每条告警需要明确触发指标与窗口、风险等级、影响范围、调查入口、响应人、立即动作、升级条件和恢复标准。

| 告警 | 建议动作 |
|---|---|
| 任何 Hard Gate 事件 | 立即暂停相关能力并升级安全/风险 |
| P95 连续超 15 秒 | 检查模型、RAG、工具阶段，必要时降级 |
| 单任务成本突增 | 限制步骤、重试和 Token，检查循环 |
| 工具拒绝率上升 | 检查权限、Schema 和下游变更 |
| 引用支持率下降 | 暂停自动建议，检查知识与检索 |
| 人工覆盖率突增 | 检查新版本质量与输入漂移 |
| Trace 缺失或关联失败 | 停止扩大流量，恢复审计能力 |

避免为每个波动都触发 Pager。告警应对应需要立即采取的动作；其余趋势进入 Dashboard 和日常复审。

---

## 十二、降级、Kill Switch 与回滚

### 12.1 能力降级阶梯

1. 切换更稳定的模型或 Prompt；
2. 关闭长期记忆；
3. 禁用高风险工具，仅保留只读工具；
4. 强制所有结果人工复核；
5. 切换为 RAG 问答或固定 Workflow；
6. 切换为人工流程；
7. 完全停止 Agent 服务。

### 12.2 Kill Switch 的粒度

可以按 Release、模型、工具、租户、用户群、业务场景、写操作、记忆写入、外部数据源或全部 Agent 能力进行控制。

### 12.3 回滚不等于恢复

回滚代码或 Prompt 只能阻止新错误，不能自动撤销已经发生的业务动作。

对有副作用的工具，需要：

- 幂等键和操作前快照；
- 可撤销接口或补偿交易；
- 受影响对象清单；
- 人工修复及客户与合规通知流程。

必须区分：

- **Technical rollback**：恢复旧版本；
- **Business compensation**：纠正已经产生的业务影响；
- **Data remediation**：删除、修正或隔离错误数据和记忆。

---

## 十三、Agent 事件响应

| 等级 | 示例 | 初始动作 |
|---|---|---|
| Sev 1 | 客户数据泄漏、未授权资金动作、系统性审批绕过 | Kill Switch、事件指挥、立即升级 |
| Sev 2 | 高风险错误建议影响多个用户、关键审计缺失 | 暂停相关能力、限制流量 |
| Sev 3 | 局部质量下降、延迟或成本显著超标 | 降级、修复、加强抽样 |
| Sev 4 | 无业务影响的小缺陷 | 进入 Backlog 与常规发布 |

响应步骤：

1. Detect：确认告警、用户反馈或业务异常；
2. Contain：停止扩散，关闭工具、版本或用户范围；
3. Preserve：保存 Trace、版本、授权与业务证据；
4. Assess：判断数据、用户、动作和时间范围；
5. Remediate：修复技术与业务影响；
6. Validate：离线回归、红队复测和 Canary 验证；
7. Recover：按批准范围恢复；
8. Learn：复盘并更新测试集、Runbook 和控制。

不要只问“模型为什么这样回答”，还要检查为何确定性控制没有阻止影响。

---

## 十四、从用户反馈到评估集

```text
线上信号或用户反馈
        ↓
关联 Trace 与 Release Bundle
        ↓
问题分类：数据 / Prompt / RAG / 工具 / 权限 / 模型 / 流程
        ↓
确认业务与风险影响
        ↓
生成可复现测试用例
        ↓
修复并运行完整回归
        ↓
Canary 验证
        ↓
更新评估集、门槛和 Runbook
```

### 14.1 反馈分类

- 正确答案被用户拒绝：可能是 UX 或信任问题；
- 错误答案被用户接受：风险更高，需要抽检与教育；
- Agent 转人工：可能是正常控制，也可能是能力不足；
- 工具被拒绝：可能是攻击被阻断，也可能是权限配置错误；
- 高成本任务：可能是复杂场景，也可能是循环或重试缺陷。

因此，单一“点赞/点踩”不能直接代表模型质量。

---

## 十五、运营节奏

| 节奏 | 建议活动 |
|---|---|
| 实时 | Hard Gate、可用性、延迟、成本异常与关键工具告警 |
| 每日 | 失败任务、人工接管、异常成本和安全事件检查 |
| 每周 | 质量抽样、用户反馈、漂移和问题趋势复盘 |
| 每次发布 | 完整回归、红队子集、Go/No-Go 和 Canary |
| 每月 | 风险、SLO、成本、采纳和供应商复审 |
| 每季度 | 场景范围、权限、数据、评估集与退出策略复审 |

频率应按场景风险和使用量调整。高风险、刚上线或快速变化阶段需要更密集的观察。

---

## 十六、角色与责任

| 角色 | 上线前 | 上线后 |
|---|---|---|
| Business Owner | 确认价值、范围和 UAT | 审查业务结果与反馈 |
| Product / Project Manager | 组织 Gate、依赖、风险和决策包 | 运营节奏、问题闭环和路线图 |
| Agent Engineering | 版本、测试、Runbook 和回滚 | 修复行为、质量与成本问题 |
| Platform / SRE | 容量、SLO、Telemetry 和发布机制 | 告警、事件、可靠性与成本 |
| Security | 红队、漏洞和控制验证 | 安全监控与事件响应 |
| Data / Privacy | 数据使用、留存和脱敏批准 | 数据事件和用途复审 |
| Risk / Compliance | Hard Gate 与剩余风险决策 | 周期复审、监管和审计支持 |
| Operations / Reviewer | 人工流程与培训 | 接管、抽检和用户反馈 |
| Internal Audit | 审查控制设计与证据 | 验证控制持续执行 |

模型供应商不能替银行承担最终的业务、数据和合规责任。

---

## 十七、Payment Investigation Agent 上线清单

### 17.1 范围与权限

- [ ] 只覆盖已批准的支付调查类型。
- [ ] 默认只读，不自动修改支付状态。
- [ ] 用户、Agent 与工具身份可追踪。
- [ ] 客户、账户和机构级权限在数据源端校验。
- [ ] 高风险动作需要独立审批。

### 17.2 质量与安全

- [ ] 六维指标达到本阶段门槛。
- [ ] Hard Gate 失败为零。
- [ ] 正常、边界、失败和攻击场景均覆盖。
- [ ] 引用可追溯到有效制度或交易证据。
- [ ] 红队问题已关闭或有获批补偿控制。

### 17.3 工程与运营

- [ ] P95 延迟和成本达标。
- [ ] Trace 可跨模型、RAG、工具和审批关联。
- [ ] Dashboard、告警、Runbook 和值班人已就绪。
- [ ] Canary 范围、观察窗口和停止条件明确。
- [ ] Kill Switch、降级和回滚已演练。
- [ ] 业务补偿和数据修复流程已准备。

### 17.4 治理与证据

- [ ] Release Bundle 完整锁定。
- [ ] 数据、隐私、安全、风险与业务签署完成。
- [ ] 已知问题、Owner、期限和剩余风险有记录。
- [ ] 用户培训、使用边界和反馈渠道已建立。
- [ ] 下一次复审日期和退出条件明确。

---

## 十八、课堂练习

### 练习 A：做一次 Go/No-Go 判断

候选版本结果如下：Business Outcome 92%、Agent Behavior 84%、Answer Correctness 91%、Security and Compliance 96%、P95 13 秒、平均成本 USD 0.08、Human Adoption 82%，但发现 1 次跨用户交易记录访问。

问题：能否进入 Canary？

**参考判断：不能。** 所有平均指标虽已达标，但跨用户访问命中 Security Hard Gate。必须修复数据源端授权与隔离，完成原用例和变体回归后重新申请准入。

### 练习 B：设计 Canary

为 20 名支付运营用户设计两周 Pilot，明确用户和调查类型、只读或写权限、任务上限、观察指标、停止条件、人工接管、稳定流程以及每日与每周复审人。

### 练习 C：设计 Kill Switch

选择“支付查询工具返回错误客户记录”事件，回答：关闭哪个粒度的能力、如何保留正常业务、如何定位受影响任务、如何修复记忆、需要谁批准恢复。

---

## 十九、自测题

1. 为什么 Agent 的发布对象不是单一代码版本？
2. Shadow、Canary、Pilot 和 Blue-Green 有什么区别？
3. Hard Gate 与普通阈值有什么不同？
4. 为什么 Trace 必须包含 Prompt、RAG、工具和策略版本？
5. 线上随机抽样为什么不足？
6. Kill Switch 应该有哪些粒度？
7. 为什么代码回滚不能代替业务补偿？
8. 用户采纳率下降可能有哪些不同原因？
9. 如何把一次生产问题转化为长期回归能力？
10. Go/No-Go 决策包中必须保留哪些证据？

---

## 二十、本课完成标准

- [x] 能定义一个完整的 Agent Release Bundle。
- [x] 能解释分阶段发布路径和每阶段退出条件。
- [x] 将六维指标、Hard Gate 和证据转成上线准入清单。
- [x] 为 Payment Investigation Agent 设计 Canary。
- [x] 定义 Metrics、Logs、Traces 和线上抽样策略。
- [x] 设计分级 Kill Switch、降级、回滚与补偿流程。
- [x] 建立从反馈到评估集再到发布的运营闭环。
- [x] 能主持一次跨职能 Go/No-Go 评审。

> 理论学习已经完成；正式 Release Gate、Canary、Kill Switch 与回滚演练将在第六周 PoC 阶段执行并留存证据。

---

## 二十一、延伸阅读

- [NIST AI RMF Core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)：用 Govern、Map、Measure、Manage 组织 AI 风险管理。
- [NIST AI RMF Playbook — Manage](https://airc.nist.gov/airmf-resources/playbook/manage/)：关注持续监控、事件、反馈和风险响应。
- [Google Cloud：Deploy and operate generative AI applications](https://docs.cloud.google.com/architecture/deploy-operate-generative-ai-applications)：参考生成式 AI 的版本、评估、部署与运行实践。
- [Google SRE Workbook：Canarying Releases](https://sre.google/workbook/canarying-releases/)：理解小流量验证和候选版本对照。
- [OpenTelemetry](https://opentelemetry.io/)：参考跨服务 Metrics、Logs 和 Traces 的统一观测思路。
- [Datawhale Hello-Agents](https://github.com/datawhalechina/hello-agents)：结合第 12 章评估内容复习上线指标与持续评估。

> 外部框架与工具会持续演进。本课用于学习与 PoC 设计，实际生产准入必须遵循所在银行的安全、风险、数据、法律、合规、变更和运营流程。

---

## 二十二、下一阶段预告

第五周结束后进入第六周 **银行 Agent PoC 与项目方案**：

- 明确 PoC 场景、用户、范围和非目标；
- 实现受控数据分析或 Payment Investigation Agent 最小流程；
- 建立 10～30 条最小评估集并运行首份报告；
- 应用本课的 Release Gate、Trace、Canary 和 Kill Switch；
- 形成项目章程、架构、验收标准和试点路线图。
