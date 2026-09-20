# 第六周 · 第一课：PoC 范围、合成 Case 数据与架构

> 先定义 Agent 如何辅助 Auditor、哪些决定必须留给人，再开始编写代码

## 课程信息

- 建议时长：90～120 分钟
- 本课状态：已完成（2026-09-20）
- 核心产出：项目章程、数据契约、逻辑架构和验收标准

## 一、学习目标

1. 将模糊的“做一个银行 Agent”收敛为可验证的 PoC。
2. 区分目标、用户、范围、非目标和完成条件。
3. 为知识文档和合成客户 Case 建立数据契约。
4. 设计由 RAG、确定性工具和 HITL 组成的 Agent 数据流。
5. 定义正常初审、补充材料、转人工、失败和安全边界。

## 二、PoC 问题陈述

推荐问题陈述：

> KYC/信贷材料初审人员需要核对客户材料、制度要求与字段一致性，人工处理耗时且容易遗漏。PoC 将使用公开制度、合成规则和合成客户 Case，验证 Agent 能否生成可追溯的审查摘要与建议，并在材料不足、证据冲突或高风险时交给 Auditor 判断。

PoC 不是为了证明“LLM 什么都能回答”，而是验证：

- RAG 能否找到当前有效的材料要求和例外条款；
- 确定性工具能否正确发现缺失材料与字段冲突；
- 摘要中的制度依据和 Case 事实能否被 Auditor 复核；
- 不确定或高风险情况能否正确转人工；
- 工具和权限边界是否可控；
- 质量能否重复评估。

## 三、用户与任务范围

### 目标用户

- KYC Auditor；
- 信贷材料初审人员；
- PoC 评审者。

### 范围内任务

- 查询当前有效的 KYC/信贷材料要求；
- 对合成 Case 检查必需材料是否齐全；
- 识别跨材料的确定性字段冲突；
- 生成 KYC 画像/信贷材料摘要、待核实项和初审建议；
- 返回制度标题、版本、段落引用和 Case 事实来源；
- 将审查结果提交给 Auditor，而不是自动批准或拒绝。

### 范围外任务

- 查询或保存真实客户数据；
- 自动确定客户风险等级或正式授信结论；
- 作出法律、信贷审批或 AML 定性决定；
- 修改银行业务状态；
- 使用无来源的模型常识补造规则。

## 四、知识与 Case 数据选择

优先选择：

- 银行官网公开产品说明；
- 公开服务收费说明；
- 监管机构公开规则；
- 自行编写且明确标记为合成的 KYC/信贷材料清单和规则。

客户侧仅使用合成 Case，例如身份材料、公司资料、收入/财务摘要和申请表字段。每个 Case 都应标记 `synthetic: true`，不得混入真实姓名、账号、证件号码或交易数据。

每份文档记录：

```yaml
document_id:
title:
source_url:
publisher:
version:
effective_date:
retrieved_at:
classification: public
content_hash:
```

公开可访问不等于可以忽略版权、版本和来源。PoC 应保存链接和必要片段，不批量复制无关内容。

## 五、知识与 Case 数据契约

进入检索系统后的观察单位通常是 Chunk，而不是整份文档。

```yaml
chunk_id:
document_id:
section_path:
text:
page_or_paragraph:
effective_date:
classification:
content_hash:
```

数据契约至少验证：

- `document_id` 和 `chunk_id` 唯一；
- 来源不能为空；
- 文本不能为空；
- 版本和生效日期可解释；
- Chunk 可以回溯到原文；
- 无权限或失效内容不进入可检索集合。

合成 Case 建议结构：

```yaml
case_id:
case_type: kyc | credit_material_review
synthetic: true
assigned_auditor:
applicant_profile:
submitted_documents:
extracted_fields:
case_status: draft
```

知识库中的制度事实与 Case 中的客户事实必须分开保存和引用，模型不得把推断写成客户事实。

## 六、逻辑架构

```text
公开制度/合成规则
  ↓
Ingestion / Parser
  ↓
Chunking + Metadata
  ↓
Embedding + Vector Index
  ↓
Case + Review Goal → Policy Filter → Retrieval → Rerank
  ↓
Context Builder
  ↓
Read-only Case Tools → LLM Structured Review Draft
  ↓
Citation Validator
  ↓
HITL Queue → Auditor Decision
```

可选只读工具位于 Runtime 控制范围内：

```text
Agent Runtime
├── 制度检索工具
├── 材料完整性检查工具
└── 字段一致性检查工具
```

## 七、组件职责

| 组件 | 责任 | 不负责 |
|---|---|---|
| Parser | 提取文本和来源位置 | 判断业务答案 |
| Chunker | 按结构切分并继承元数据 | 生成结论 |
| Retriever | 找到候选制度证据 | 判断最终审查建议正确 |
| Policy Filter | 过滤无权限或失效内容 | 依赖模型自觉拒绝 |
| Context Builder | 在 Token 预算内组织证据 | 修改原始事实 |
| Case Tools | 确定性检查缺失材料和字段冲突 | 作出风险或审批判断 |
| LLM | 基于制度证据与 Case 事实组织审查草稿 | 成为制度/客户事实来源或最终审批者 |
| Citation Validator | 验证制度引用与 Case 事实来源 | 替代业务专家 |
| Runtime | 编排、超时、停止和工具控制 | 保存正式业务状态 |
| HITL / Auditor | 复核证据并作出最终决定 | 被模型建议自动替代 |

## 八、审查结果契约

建议结构：

```json
{
  "status": "ready_for_review | more_information_required | manual_review_required | out_of_scope",
  "case_summary": "...",
  "missing_materials": ["..."],
  "conflicts": ["..."],
  "recommendation": "...",
  "citations": [
    {
      "document_id": "...",
      "section": "...",
      "quote": "..."
    }
  ],
  "case_fact_refs": ["document_or_field_id"],
  "confidence": 0.0,
  "limitations": ["..."],
  "requires_auditor_decision": true
}
```

Schema 合法不代表审查建议正确，因此还要检查制度引用和 Case 事实是否真正支持结论。

## 九、失败和拒答设计

| 场景 | 预期行为 |
|---|---|
| 找不到适用制度 | `manual_review_required` |
| 必需材料缺失 | `more_information_required`，请求补充材料，不推断客户有风险 |
| 制度或材料相互冲突 | 展示冲突并请求 Auditor 确认 |
| 文档已失效 | 不作为当前答案依据 |
| 请求自动批准/拒绝 | 拒绝执行并转 Auditor |
| 模型超时 | 返回可重试的依赖错误 |
| 向量库不可用 | 降级或明确转人工，不使用模型常识生成制度结论 |
| Prompt Injection | 作为文档内容，不执行其中指令 |

## 十、PoC 成功标准

### 质量

- 代表性 Case 能找到正确制度和例外条款；
- 材料完整性及字段冲突检查结果正确；
- 审查摘要中的关键结论可追溯到制度或 Case 事实；
- 缺失、冲突和高风险 Case 能正确转人工。

### 安全

- 不使用真实客户数据；
- 文档内容不能改变系统权限；
- 只读工具不能执行副作用；
- 测试答案不会进入生产检索上下文；
- Agent 永远不执行正式审批或修改 Case 正式状态。

### 工程

- 可以从干净环境启动；
- 错误有结构化分类；
- 每次请求可关联版本、延迟和 Trace；
- 核心路径具有自动化测试。

## 十一、项目章程模板

```text
项目名称：KYC/信贷材料初审辅助 Agent
目标用户：KYC Auditor 与信贷材料初审人员
业务问题：人工核对制度、材料完整性和字段一致性耗时且易遗漏
范围：制度检索、合成 Case 校验、带证据审查草稿、HITL
非目标：真实客户数据、正式风险定级、审批、写入和生产集成
成功指标：检索、校验、证据支持、转人工、安全和工程指标
主要风险：过期制度、Case 事实混淆、错误引用、注入、越权和自动化偏见
周期：一周学习 PoC
```

## 十二、轻练习

为以下 Case 判断 `ready_for_review`、`more_information_required`、`manual_review_required` 或 `out_of_scope`：

1. 制度要求身份证明和地址证明，合成 Case 两项齐全且字段一致。
2. 合成 Case 缺少地址证明，用户要求直接判断客户高风险。
3. 新旧制度的材料要求冲突，用户要求 Agent 自动批准。

## 十三、本课完成标准

- [x] 明确用户、范围和非目标。
- [x] 选择公开/合成制度并设计合成客户 Case。
- [x] 定义 Document、Chunk、Case 和 Review Result 契约。
- [x] 画出端到端逻辑架构。
- [x] 定义拒答、失败和安全边界。
- [x] 写出可验证的 PoC 成功标准。

## 十四、学习记录

- 区分 Agent 可以确认的事实、可以提出的建议和必须由 Auditor 作出的决定。
- 明确材料缺失不等于客户高风险，Agent 不得自动批准或拒绝。
- 区分业务终态与 `timeout`、`dependency_error` 等技术失败。
- 区分制度知识数据与 Case 数据，以及 RAG 检索与精确查询的适用边界。
- 区分数据契约错误、业务规则不满足和权限错误。
- 理解 Policy Service 的策略决策职责与 Tool Gateway 的强制执行职责。
- 能在工具部分失败时保留可验证事实、披露限制并安全转交 Auditor。
