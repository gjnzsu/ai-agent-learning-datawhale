# 第二周 · 第二课：Plan-and-Solve 与 Reflection

> 适合角色：银行 AI 平台项目经理；建议用时：90～120 分钟。前置知识：理解 ReAct 与受控工具调用。本课重点：掌握“先规划后执行”和“生成后评审修正”两种范式，并判断它们在银行场景中的适用边界。

## 资料来源与改编说明

本课以 Datawhale Hello-Agents [第四章《智能体经典范式构建》](https://github.com/datawhalechina/hello-agents/blob/main/docs/chapter4/%E7%AC%AC%E5%9B%9B%E7%AB%A0%20%E6%99%BA%E8%83%BD%E4%BD%93%E7%BB%8F%E5%85%B8%E8%8C%83%E5%BC%8F%E6%9E%84%E5%BB%BA.md)中的 Plan-and-Solve 与 Reflection 为主线。原教程将 Plan-and-Solve 概括为规划和执行两个阶段，将 Reflection 概括为执行、反思和优化的迭代过程。

本讲义针对银行 AI 平台补充：

- 计划审批、计划版本和动态重规划。
- 计划步骤与工具权限的分离。
- 基于规则、证据和测试的 Reflection。
- 防止“模型自评模型”形成虚假可靠性。
- KYC 审查辅助和运营分析案例。

## 一、本课目标

完成本课后，你应该能够：

1. 解释 Plan-and-Solve 的 Plan 与 Solve 两个阶段。
2. 解释 Reflection 的 Execute、Review 与 Refine 三个阶段。
3. 比较 ReAct、Plan-and-Solve 和 Reflection 的差异。
4. 判断什么时候需要重新规划，而不是继续执行旧计划。
5. 设计有明确标准和停止条件的评审机制。
6. 为银行场景选择单一范式或组合范式。

## 二、先回顾 ReAct

上一课学习的 ReAct 是一种步进式循环：

```text
Reason → Action → Observation → 下一轮 Reason
```

它适合解决路径受中间结果影响的任务。例如，运营分析 Agent 根据地区维度的结果，决定下一步分析产品还是客户类型。

ReAct 的优势是灵活，但也可能出现：

- 缺少全局计划，只关注当前一步。
- 工具调用次数多。
- 在多个方向之间反复探索。
- 难以提前估算时间和成本。

Plan-and-Solve 从另一个角度解决这些问题：先看完整任务，再开始执行。

---

## 三、Plan-and-Solve：先规划，后执行

### 1. 基本结构

```text
复杂目标
   ↓
Plan：拆分任务并形成完整计划
   ↓
检查计划、权限和依赖
   ↓
Solve：按照计划逐步执行
   ↓
汇总各步骤结果
```

规划阶段不急着调用工具，而是先回答：

- 需要完成哪些步骤？
- 步骤之间有什么依赖？
- 每一步需要什么数据或工具？
- 哪些步骤可以自动执行？
- 哪些步骤需要人工确认？
- 怎样判断整个任务完成？

### 2. KYC 场景示例

目标：为一个企业客户生成 KYC 审查辅助报告。

可能的计划是：

```text
步骤 1：确认 Case 范围和 Auditor 权限
步骤 2：检查申请材料完整度
步骤 3：读取企业基础信息和受益所有人信息
步骤 4：读取 AML 系统中已授权的风险摘要
步骤 5：检索适用的 KYC 制度条款
步骤 6：比较不同来源中的关键字段
步骤 7：汇总缺失、冲突和风险提示
步骤 8：生成带来源的审查建议，提交 Auditor
```

计划让项目团队在执行前看见整体路径，也更容易识别：

- 是否缺少关键步骤。
- 是否请求了不必要的数据。
- 是否包含未授权工具。
- 哪一步需要人工审批。
- 成本和时间是否可以接受。

## 四、计划不是执行权限

即使模型生成了一个合理计划，也不意味着计划中的所有步骤都可以执行。

```text
模型生成计划
      ↓
平台验证计划结构
      ↓
工具白名单与数据权限检查
      ↓
高风险步骤人工确认
      ↓
才进入执行阶段
```

例如，模型在计划中写出“查询客户全部交易流水”，平台仍需判断：

- 当前 KYC Case 是否真的需要这些数据。
- Auditor 是否拥有相应权限。
- 是否可以只返回聚合后的风险摘要。
- 是否涉及超出时间范围的数据。

计划表达的是模型的建议路径；授权仍由确定性平台控制。

## 五、静态计划的局限

最简单的 Plan-and-Solve 会一次生成计划，并严格执行到结束。这种静态计划存在风险：

- 某个数据源不可用，后续步骤无法继续。
- 中间结果证明原计划假设错误。
- 出现新的高风险信息，需要增加检查。
- 已经获得足够证据，却仍执行多余步骤。
- 业务人员改变任务范围。

例如：

```text
原计划：读取 KYC → 查询 AML → 生成报告

执行 KYC 查询后发现：客户身份字段冲突

如果仍严格执行原计划：可能遗漏身份核验
合理做法：暂停计划，增加身份冲突核验或转人工
```

## 六、动态重规划

动态重规划并不是每一步都重新生成整套计划。更合理的触发条件包括：

- 关键步骤失败且无法按原方案继续。
- 发现计划中没有覆盖的重要风险。
- 上游结果改变了后续步骤的前提。
- 人工修改了目标或约束。
- 权限和数据范围发生变化。

重规划过程可以是：

```text
执行计划
  ↓
检测到计划偏差
  ↓
暂停后续步骤
  ↓
保留已经验证的结果
  ↓
生成计划修订建议
  ↓
重新进行权限与人工审批
  ↓
执行新版本计划
```

建议记录：

- 原计划版本。
- 触发重规划的事实。
- 被保留、取消和新增的步骤。
- 新计划的审批结果。
- 重规划次数。

为了防止循环，应限制最大重规划次数。

## 七、Plan-and-Solve 的概念代码

```python
def run_plan_and_solve(goal, planner, executor, policy):
    plan = planner.create_plan(goal)
    policy.validate_plan(plan)
    results = []

    for step in plan.steps:
        policy.validate_step(step)

        if step.requires_approval:
            approval = request_human_approval(step, results)
            if not approval.approved:
                return build_handoff_result(plan, results)

        result = executor.execute(step, results)
        results.append(result)

        if policy.requires_replanning(step, result):
            return replan_with_context(goal, plan, results)

    return build_final_result(plan, results)
```

需要理解的不是 Python 语法，而是职责分离：

- Planner 生成计划。
- Policy 校验计划和单个步骤。
- Executor 执行被允许的步骤。
- Human Approval 控制高风险行动。
- Replanning 处理计划偏差。

---

## 八、Reflection：生成、评审、修正

Reflection 解决的问题是：Agent 已经得到一个结果，但结果可能仍有遗漏、矛盾或质量问题。

```text
Execute：生成初稿
    ↓
Review：依据标准检查初稿
    ↓
Refine：根据反馈修订
    ↓
通过标准或达到迭代上限
```

它类似于软件开发中的：

```text
编写代码 → Code Review / Tests → 修复问题
```

关键并不只是“再问一次模型”，而是给评审阶段提供明确标准和可靠证据。

## 九、KYC 报告的 Reflection 示例

### 初稿

Agent 生成：

> 客户资料基本完整，建议通过 KYC 审查。

这份初稿存在明显问题：结论缺少来源，也没有说明“基本完整”具体指什么。

### 评审标准

```text
1. 是否列出所有必需材料？
2. 是否说明每项信息的来源和更新时间？
3. 是否存在未解释的数据冲突？
4. 建议是否得到规则和证据支持？
5. 是否包含超出 Agent 权限的最终审批措辞？
6. 是否泄露不必要的敏感信息？
```

### 评审反馈

```json
{
  "status": "REVISION_REQUIRED",
  "issues": [
    "缺少材料完整度明细",
    "没有展示证据来源",
    "建议通过的措辞超出辅助系统职责"
  ]
}
```

### 修订稿

```text
已完成 7 项必要材料检查，其中 6 项有效；受益所有人证明已过期。
KYC 系统与申请表中的注册名称存在格式差异，统一社会信用代码一致。
建议 Auditor 要求更新受益所有人证明，并确认名称差异后继续审查。
```

修订稿没有代替 Auditor 作出最终审批，同时更加具体、可追溯。

## 十、Reflection 不能等同于事实核验

如果同一个模型生成初稿，再让同一个模型“反思”，它可能重复原来的错误。

以下方式更可靠：

| 检查对象 | 优先方式 |
| --- | --- |
| 日期、金额、字段完整度 | 确定性代码或规则 |
| 制度引用是否存在 | 检索系统与引用校验 |
| 图表与数据是否一致 | 程序化数据校验 |
| 是否包含敏感字段 | DLP、字段规则和安全策略 |
| 文本是否清晰完整 | LLM Reviewer 可以辅助 |
| 最终高风险判断 | 业务专家或 Auditor |

因此，Reflection 更适合被理解为“评审与改进流程”，而不是给模型增加一个万能的自我纠错按钮。

## 十一、评审者如何设计

Reflection 可以使用不同的评审者：

### 同一模型评审

- 成本和集成复杂度较低。
- 容易继承相同盲点。

### 不同模型评审

- 可能提供不同视角。
- 成本更高，仍不能保证事实正确。

### 规则与工具评审

- 适合检查确定性条件。
- 可复现、可解释，但难以评价开放文本的全部质量。

### 人工评审

- 适合高影响结论和疑难案例。
- 成本较高，需要设计清晰的接管界面。

银行场景通常采用混合评审：

```text
规则校验硬约束
工具校验证据
LLM 检查表达和遗漏
Auditor 作出最终判断
```

## 十二、Reflection 的停止条件

不应让 Reviewer 无限要求修改。常见停止条件包括：

- 所有必需检查均通过。
- 质量评分达到预设阈值，并且没有严重问题。
- 达到最大修订次数。
- 连续两次修订没有实质改进。
- 需要的新证据无法取得。
- 发现必须由人工判断的问题。
- 达到时间或成本预算。

达到迭代上限不代表结果合格。正确状态可能是：

```text
REVIEW_PASSED
REVISION_LIMIT_REACHED
EVIDENCE_INSUFFICIENT
HUMAN_REVIEW_REQUIRED
```

## 十三、Reflection 的概念代码

```python
def run_with_reflection(task, generator, reviewers, max_rounds=2):
    draft = generator.create(task)

    for round_number in range(max_rounds):
        feedback = [reviewer.review(task, draft) for reviewer in reviewers]

        if all(item.passed for item in feedback):
            return build_result("REVIEW_PASSED", draft, feedback)

        if any(item.requires_human for item in feedback):
            return handoff_to_human(draft, feedback)

        draft = generator.refine(task, draft, feedback)

    return build_result("REVISION_LIMIT_REACHED", draft, feedback)
```

这里的 `reviewers` 可以同时包含规则校验器、证据校验器和 LLM Reviewer。

---

## 十四、三种范式的比较

| 范式 | 核心问题 | 优势 | 主要风险 |
| --- | --- | --- | --- |
| ReAct | 下一步应该做什么？ | 灵活适应工具反馈 | 循环、成本和路径漂移 |
| Plan-and-Solve | 整个任务如何分解？ | 结构清晰，便于估算和审计 | 静态计划可能失效 |
| Reflection | 当前结果哪里需要改进？ | 提高完整性和表达质量 | 自评偏差与额外成本 |

可以用三个动词记忆：

```text
ReAct：边做边调整
Plan-and-Solve：先规划再执行
Reflection：做完再检查修正
```

## 十五、怎样选择范式

### 优先考虑 ReAct

- 中间结果会明显改变下一步。
- 需要探索多个数据源或工具。
- 无法提前确定完整路径。

### 优先考虑 Plan-and-Solve

- 任务可以分成清晰步骤。
- 步骤之间存在明确依赖。
- 需要在执行前评审计划、权限和成本。

### 增加 Reflection

- 输出是重要报告、建议或代码。
- 存在明确的质量标准。
- 允许用更多时间和成本换取质量。

### 保持普通 Workflow

- 所有步骤和分支已经确定。
- 不需要模型动态规划。
- 确定性和低延迟比灵活性更重要。

## 十六、银行场景中的组合方式

KYC 审查辅助可以组合三种范式：

```text
Plan-and-Solve
先生成审查计划，并由平台验证权限
        ↓
ReAct
在某个检查步骤内，根据查询结果选择后续工具
        ↓
Reflection
对最终报告进行规则、证据和文本质量检查
        ↓
Human Review
Auditor 作出最终决定
```

组合越多，成本、延迟和排错难度也越高。PoC 不需要一开始就使用全部机制，可以先验证最关键的价值假设。

## 十七、项目经理评审清单

### Plan 评审

- 计划是否覆盖业务目标？
- 步骤依赖是否正确？
- 是否包含不必要的数据访问？
- 工具和权限是否匹配？
- 哪些步骤需要人工审批？
- 失败后是否可以重规划或降级？

### Reflection 评审

- 评审标准是否明确？
- 哪些检查由规则完成？
- 哪些检查需要检索证据？
- LLM Reviewer 的输出如何验证？
- 最大修订次数是多少？
- 未通过时是否会错误地作为成功输出？

## 十八、配套视频

### 中文必看

- [Datawhale：Hello-Agents 第四章——智能体范式构建（上）](https://www.bilibili.com/list/431850986?bvid=BV12Z63BCEn6&oid=115967673769704)
  - 重点观看 Plan-and-Solve 和 Reflection 的概念及运行日志。

### 英文选看

- [Agentic AI — Andrew Ng / DeepLearning.AI](https://www.deeplearning.ai/courses/agentic-ai)
  - 选择 Planning 和 Reflection 相关视频。
- [AI Agents in LangGraph — DeepLearning.AI](https://www.deeplearning.ai/courses/ai-agents-in-langgraph)
  - 可观察框架如何表示状态、步骤和人工介入。

## 十九、本课学习方式

### 第一段：Plan-and-Solve，约 35 分钟

阅读第三至第七节，理解规划、执行和动态重规划。

### 第二段：Reflection，约 35 分钟

阅读第八至第十三节，理解评审、修订和停止条件。

### 第三段：选择与组合，约 20 分钟

阅读第十四至第十七节，形成项目选型视角。

## 二十、轻量练习

本课设置三项练习，完成一段学习后再做对应练习：

1. 为 KYC 审查辅助任务写出一个 5～8 步的计划。
2. 为 KYC 报告写出三个可验证的 Reflection 检查项。
3. 说明一个场景为什么选择 ReAct、Plan-and-Solve、Reflection 或组合方案。

## 二十一、本课验收标准

- [ ] 能解释 Plan 与 Solve 的职责差异。
- [ ] 能说明计划为什么不等于执行权限。
- [ ] 能给出至少两个动态重规划触发条件。
- [ ] 能解释 Execute、Review 和 Refine 循环。
- [ ] 能说明 LLM 自我反思为什么不等于事实核验。
- [ ] 能为 Reflection 设计评审标准和停止条件。
- [ ] 能比较并选择三种经典范式。

本课完成后，将进入第二周第三课：Human-in-the-loop 与执行治理。
