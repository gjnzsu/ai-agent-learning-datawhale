# 第二周 · 第一课：ReAct 与受控工具调用

> 适合角色：银行 AI 平台项目经理；建议用时：90～120 分钟。前置知识：能够区分规则、Workflow、LLM 应用与 Agent。本课重点：理解 ReAct 循环，以及如何把工具调用限制在可控边界内。

> 学习状态：**已完成**；完成日期：2026-09-04。验收结果：能够解释 ReAct 循环，设计受控工具及失败处理，并理解停止条件、人工接管和 Agent Loop 的平台控制职责。

## 资料来源与改编说明

本课以 Datawhale Hello-Agents [第四章《智能体经典范式构建》](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA.md)为主线。原教程介绍了 ReAct、Plan-and-Solve 和 Reflection 三种经典范式，并通过 LLM 客户端、工具执行器和 Agent 循环展示其实现方式。

本讲义将第一课聚焦在 ReAct，并针对银行 AI 平台增加：

- 工具白名单、只读权限与参数约束。
- 人工审批、停止条件与失败降级。
- 审计日志和决策依据记录。
- KYC 审查辅助 Agent 案例。

## 一、本周学习地图

第二周建议分为三个课时：

| 课时 | 内容 | 主要产出 |
| --- | --- | --- |
| 第一课 | ReAct 与受控工具调用 | 看懂 Agent 的行动循环和工具边界 |
| 第二课 | Plan-and-Solve 与 Reflection | 比较三种范式及适用场景 |
| 第三课 | Human-in-the-loop 与执行治理 | 工具清单、审批矩阵和停止策略 |

本课先建立运行机制，不要求立即写完整代码。

## 二、本课目标

完成本课后，你应该能够：

1. 解释 ReAct 中 Reason、Action 和 Observation 的关系。
2. 区分初始输入、工具返回结果和最终答案。
3. 看懂一个 Agent Loop 的概念代码。
4. 说明工具描述、输入输出和权限为什么同样重要。
5. 为银行 Agent 设计超时、重试、人工接管和停止条件。

## 三、为什么需要 ReAct

只调用一次 LLM 时，模型主要依据输入和预训练知识生成回答：

```text
用户问题 → LLM → 回答
```

它可能遇到三个问题：

- 不知道内部系统中的实时数据。
- 不擅长精确计算和确定性校验。
- 无法真正执行查询、计算或业务操作。

ReAct 将推理与行动连接起来：

```text
目标
  ↓
判断下一步需要什么信息
  ↓
选择并调用工具
  ↓
观察工具结果
  ↓
根据结果继续、调整、转人工或结束
```

其核心不是“让模型想得更久”，而是让模型的决策能够得到外部事实反馈。

## 四、ReAct 的三个基本元素

### 1. Reason：决策依据

模型分析当前状态，并决定下一步需要做什么。

教程通常使用 `Thought` 表示这一阶段。在企业系统中，不建议把模型完整的内部思维过程当作审计记录，也不应依赖冗长的自然语言思考来证明合规。

更适合记录的是结构化决策摘要：

```json
{
  "current_status": "客户姓名在两个来源中不一致",
  "next_action": "compare_identity_fields",
  "reason_code": "IDENTITY_DATA_CONFLICT",
  "required_approval": false
}
```

### 2. Action：具体行动

Action 通常是调用一个被平台注册的工具，例如：

```text
query_kyc_profile(customer_reference)
compare_identity_fields(source_a, source_b)
retrieve_policy(policy_topic, user_scope)
calculate_data_completeness(case_id)
request_human_review(case_id, reason_code)
```

模型只能从平台允许的工具中选择，不能临时编造一个可执行工具。

### 3. Observation：工具反馈

Observation 是工具真正执行后返回的结果，例如：

```json
{
  "status": "conflict",
  "fields": ["customer_name"],
  "source_a": "KYC_SYSTEM",
  "source_b": "APPLICATION_FORM",
  "matched_identity_id": true
}
```

Observation 不是模型猜测的结果，也不是 Agent 开始任务前已有的全部数据。它是行动执行后，环境返回给 Agent 的新信息。

## 五、KYC 审查辅助案例

任务：

> 汇总客户 KYC 资料，识别缺失和冲突信息，生成审查建议，由 KYC Auditor 最终确认。

一次受控 ReAct 过程可以是：

```text
目标：生成可追溯的 KYC 审查辅助意见

决策摘要：需要先确认基础资料是否齐全
Action：调用 KYC 资料完整度检查工具
Observation：公司受益所有人证明缺失

决策摘要：材料不完整，继续查询是否存在有效历史材料
Action：调用历史材料索引工具
Observation：存在一份已过有效期的历史材料

决策摘要：当前证据不足，不能给出通过建议
Action：生成补件建议并提交 Auditor
Observation：Auditor 已接收，等待人工决定

Finish：输出缺失项、证据来源和建议，不执行最终审批
```

这个过程中的重点是：

- Agent 没有把“材料缺失”直接解释成客户高风险。
- Agent 继续查询了被允许访问的历史材料。
- 发现证据不足后，Agent 没有无限搜索。
- 补件建议交给 Auditor，而不是直接联系客户。
- 最终审批仍属于人工职责。

## 六、工具不是一个普通函数名

一个可以交给 Agent 的工具至少需要定义以下内容：

| 项目 | 需要回答的问题 |
| --- | --- |
| 名称 | 模型如何准确选择它？ |
| 用途描述 | 什么时候应该或不应该使用？ |
| 输入契约 | 必填参数、类型、长度和允许值是什么？ |
| 输出契约 | 成功、无数据、失败分别如何表达？ |
| 身份与权限 | 以谁的身份访问哪些数据？ |
| 数据范围 | 能读取哪个客户、机构和时间范围？ |
| 副作用 | 是否会修改数据或触发外部行为？ |
| 超时与重试 | 失败后可以重试几次？ |
| 幂等性 | 重复调用会不会造成重复操作？ |
| 审计信息 | 记录谁在何时因为什么调用了工具？ |

工具描述过于模糊时，模型容易选错工具。例如：

```text
不清楚：get_data —— 获取数据

更清楚：get_kyc_profile —— 只读查询指定 KYC case 的客户基础资料；
不得用于查询交易明细，也不会修改客户信息。
```

## 七、银行工具权限分级

| 级别 | 示例 | 首期建议 |
| --- | --- | --- |
| 只读查询 | 查询 KYC 状态、检索制度 | 可在授权范围内自动调用 |
| 确定性计算 | 完整度计算、日期和规则校验 | 可自动调用并记录输入输出 |
| 生成草稿 | 生成摘要、补件建议 | 可自动生成，但由人确认 |
| 可撤销写操作 | 创建草稿工单 | 通常需要审批或严格限定 |
| 高影响操作 | 审批、拒绝、冻结、转账 | 不交给 LLM Agent 自主执行 |

一条实用原则是：

> Agent 可以自主选择低风险工具，但不能因此自动获得工具背后系统的全部权限。

工具网关应根据当前用户身份、业务角色和 case 范围再次鉴权，而不是相信模型传入的参数。

## 八、失败处理不是让 Agent“一直试”

工具调用常见结果包括：

- 成功并返回数据。
- 成功但没有数据。
- 参数无效。
- 无权访问。
- 系统超时或暂时不可用。
- 返回数据不完整或相互冲突。

不同结果需要不同处理：

| 结果 | 推荐处理 |
| --- | --- |
| 无数据 | 标记“未查询到”，不能解释为客户不存在 |
| 参数无效 | 修正一次；仍失败则转人工或结束 |
| 无权访问 | 立即停止，不尝试绕过权限 |
| 暂时超时 | 按退避策略有限重试 |
| 持续不可用 | 降级或提交人工处理 |
| 数据冲突 | 展示来源和差异，交由规则或人工判断 |

### 超时示例

KYC 系统查询超时时，正确含义是“当前查询失败”，不是“客户资料不存在”。

推荐策略：

```text
首次超时
  ↓
间隔后重试一次
  ↓ 仍然失败
记录失败来源和时间
  ↓
停止该查询路径，转人工或稍后重试
```

## 九、必须预先设计停止条件

如果只让模型自行判断“我是否完成”，Agent 可能过早停止，也可能陷入循环。

常见停止条件包括：

- 已满足任务验收条件。
- 已达到最大步骤数。
- 已达到单工具最大重试次数。
- 达到总超时时间或成本预算。
- 需要的关键数据无权访问。
- 高风险规则命中，必须转人工。
- 工具连续失败，继续执行没有意义。
- 同一行动和结果重复出现。

KYC 辅助场景可以设置：

```text
最大 Agent 步数：8
单个只读工具最大重试：2
任务总超时：按平台 SLA 配置
出现权限拒绝：立即停止相关路径
出现高风险规则：转 Auditor
证据不足：输出缺失项，不生成通过建议
```

具体数值需要通过测试和实际 SLA 校准，上述数字只用于帮助理解设计方式。

## 十、Human-in-the-loop 的三个位置

人工参与不只发生在最后一步。

### 1. 行动前审批

Agent 提出要执行的操作，人确认后才能调用工具。适合写操作或敏感查询。

### 2. 执行中接管

遇到权限不足、数据冲突、高风险规则或重复失败时，将任务和已有证据交给人工。

### 3. 结果后复核

Agent 完成摘要和建议后，由业务人员确认最终结论。KYC Auditor 的最终审批属于这一类。

## 十一、Agent Loop 概念代码

这段代码用于理解结构，不要求现在运行：

```python
def run_agent(goal, tools, max_steps=8):
    history = []

    for step in range(max_steps):
        decision = decide_next_action(goal, history, tools)

        if decision.requires_human_review:
            return handoff_to_human(decision, history)

        if decision.action == "finish":
            return build_final_result(decision, history)

        tool = tools.get(decision.tool_name)
        if tool is None:
            history.append({"error": "tool_not_allowed"})
            continue

        observation = tool.execute(decision.validated_input)
        history.append({
            "action": decision.tool_name,
            "input": decision.audit_safe_input,
            "observation": observation,
        })

    return handoff_to_human("maximum_steps_reached", history)
```

作为项目经理，不必现在掌握全部 Python 语法。需要看懂的结构是：

1. 循环有最大次数。
2. 模型只负责提出下一步行动。
3. 平台检查工具是否存在并校验输入。
4. 工具结果被写入执行历史。
5. 高风险或异常情况可以转人工。

## 十二、平台审计应记录什么

建议记录：

- Task ID、Case ID 和用户身份。
- Agent、模型、Prompt 和工具版本。
- 每一步行动名称、时间和状态。
- 脱敏后的输入参数。
- 工具返回状态和数据来源。
- 规则命中和结构化决策原因。
- 人工审批人、审批意见和时间。
- 最终结果、停止原因、耗时和成本。

避免把完整敏感数据和模型内部思维原样写入普通应用日志。日志本身也需要分级、脱敏、权限控制和保存期限。

## 十三、三个范式的初步认识

本课重点是 ReAct，先建立一个总体印象：

| 范式 | 核心方式 | 更适合的任务 |
| --- | --- | --- |
| ReAct | 边观察、边行动、边调整 | 路径受中间结果影响的任务 |
| Plan-and-Solve | 先形成计划，再逐步执行 | 结构较清晰的复杂多步骤任务 |
| Reflection | 生成后检查并修正 | 结果可以被评价和改进的任务 |

三种范式不是互斥的。一个系统可以先制定计划，在每一步使用 ReAct，并在输出前执行 Reflection。是否组合使用，应由任务价值、风险、延迟和成本共同决定。

## 十四、配套视频

### 本课必看

- [Datawhale：Hello-Agents 第四章——智能体范式构建（上）](https://www.bilibili.com/list/431850986?bvid=BV12Z63BCEn6&oid=115967673769704)
  - 先关注 ReAct 的概念、工具和循环。
  - 代码部分可以在阅读本讲义后再看。

### 英文选看

- [Agentic AI — Andrew Ng / DeepLearning.AI](https://www.deeplearning.ai/courses/agentic-ai)
  - 选择 Tool Use、Planning 和 Agentic Design Patterns 相关视频。
- [AI Agents in LangGraph — DeepLearning.AI](https://www.deeplearning.ai/courses/ai-agents-in-langgraph)
  - 选择 Build an Agent from Scratch 和 Human in the Loop。

## 十五、本课学习方式

不要一次完成全部内容。建议分三段：

### 第一段：理解循环，约 30 分钟

阅读第三至第五节，只需要理解 Reason、Action、Observation 和 KYC 示例。

### 第二段：理解工具边界，约 35 分钟

阅读第六至第十节，重点关注工具定义、权限、失败处理和停止条件。

### 第三段：形成平台视角，约 25 分钟

阅读第十一至第十三节，看懂概念代码和审计字段，不要求编码。

## 十六、本课轻量练习

本课只设置三项练习，不采用连续考试形式：

1. 在 KYC 场景中写出一组 Action 和 Observation。
2. 为一个只读查询工具写出名称、用途、输入、输出和权限。
3. 写出三个停止条件，以及一个必须转人工的条件。

可以读完一个阶段后再完成对应练习，我会先讲解你的答案，再进入下一阶段。

## 十七、本课验收标准

- [x] 能解释 ReAct 循环。
- [x] 能区分 Action 和 Observation。
- [x] 能说明模型为什么不能绕过工具网关权限。
- [x] 能为工具失败设计有限重试和降级。
- [x] 能给出明确的停止与人工接管条件。
- [x] 能看懂 Agent Loop 概念代码的主要结构。

本课完成后，再进入 Plan-and-Solve 与 Reflection，不要求在一次学习中掌握三种范式。
