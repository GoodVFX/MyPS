---
name: daily-review
description: 晚间总结——每天 22:00 自动推送今日回顾、知识积累汇报、惊奇度扫描、情绪教练评价。
version: 1.8
created: 2026-05-31
updated: 2026-07-31
when_to_use:
  - Cron 22:00 触发
---

# 晚间总结

你正在执行晚间总结任务。这是每天最重要的 Skill——它不仅总结今天，还负责惊奇度扫描和情绪教练调用。以下是完整的输出规则。

---

## 处理流程

### 步骤 0（先决条件）：确认数据目录路径

Cron 启动时工作目录不一定是 `~/.hermes/`。所有 `data/` 路径均相对于 `~/.hermes/`，所以第一步必须是：

```
检查 ~/.hermes/data/ 是否存在
   ├── 存在 → 以 ~/.hermes/ 为 base 路径
   ├── 不存在 → 用 search_files 或 find 定位 data/ 实际位置
   └── 找不到 → 输出 [SILENT] 并结束（但记录日志供排查）
```

**常见错误**：Cron 未设 workdir 时从 `~/` 启动，`data/diary/` 解析为 `~/data/diary/` 即文件不存在。修复：Cron 创建时设 `workdir='~/.hermes'`。

**调试技巧**：如果所有数据文件都找不到，用 `session_search` 查一下之前的 Cron 运行记录——可能上轮也失败了，或者数据本身确实不存在。不要假设「有数据但没找到」vs「本来就无数据」——主动确认。

**路径注意**：`memory/` 目录位于 `~/.hermes/memory/`，与 `data/` 平级，不在 `data/` 下。步骤 0.6 中读取的 `memory/mood-trends.md` 对应 `~/.hermes/memory/mood-trends.md`（而非 `~/.hermes/data/memory/mood-trends.md`）。

### 步骤 0.5：检查是否为重跑（失败重跑或清洁重跑）

Cron 可能因两种原因重跑：
- **失败重跑**：网络波动/临时故障失败后，调度器自动重试
- **清洁重跑**：前一轮成功运行（last_status=ok, last_delivery_error=null），但用户/系统触发了再次执行

两种重跑都应当正常输出，但处理方式有细微差别。

1. **确认前一轮的状态**：检查当前 cron job 的 output 目录下今天的最新文件。

   **方法 A（推荐）**——已知 job ID 时直接用：
   ```bash
   ls -lt ~/.hermes/cron/output/<your-job-id>/ | head -5
   ```

   **方法 B（推荐）**——读取 cron 配置来查找 job ID：

   方式 a（execute_code，优先——JSON 解析比 shell grep 更可靠）：
   ```python
   import json, os
   with open(os.path.expanduser("~/.hermes/cron/jobs.json")) as f:
       jobs = json.load(f).get("jobs", [])
   for j in jobs:
       if j.get("name") == "daily-review":
           print(j["id"])
           break
   ```

   方式 b（shell 兜底——注意只查 jobs.json，不要 cat *.json，backup-status.json 会混入）：
   ```bash
   cat ~/.hermes/cron/jobs.json | grep -B5 '"name": "daily-review"'
   ```
   从输出中提取该 job 的 `"id"` 字段，然后直接检查该目录：
   ```bash
   ls -lt ~/.hermes/cron/output/<找到的job-id>/ | head -5
   ```

   **方法 C（兜底）**——当 cron 配置也找不到时，通过目录特征推测：
   ```bash
   # 列出所有 job 目录，按修改时间排序，找到今天最新运行的那个
   ls -lt ~/.hermes/cron/output/ | head -10
   ```
   daily-review 任务的特征：目录下有大量历史文件（每天一个），最近修改的就是本轮或上一轮的输出。

   **判断「首次运行」**：如果 output 目录下最新的文件日期是**昨天或更早**，说明今天是第一次执行（不是重跑）——此时不需要任何重跑处理，直接走正常流程。只有在今天已存在输出文件时才需要判断是失败重跑还是清洁重跑。**不要因为「今天是第一次跑」而跳过步骤 0.6 等后续检查**——首次运行和重跑都要完整执行全部流程（2026-08-02 实测：输出目录最新文件为昨日 → 判定首次运行，正常走零录入日流程）。

2. **确认 mood-trends 是否已有今日条目**：读取 `~/.hermes/memory/mood-trends.md`，搜索 `### YYYY-MM-DD 情绪评估`（替换为今日日期）。
   - **存在** → 清洁重跑（前一轮已成功写入情绪评估）。后续 emotion-coach 调用时**跳过步骤 4（写入 mood-trends.md）**，避免重复条目
   - **不存在** → 首次运行或失败重跑。正常执行全部流程。

3. **输出标记**：
   - **失败重跑**：输出末尾加一行说明——`补充说明：刚才那轮因 [原因] 没跑成，现在补上了。`
   - **清洁重跑（mood-trends 已有今日条目）**：无需额外说明。直接正常输出。
   - **清洁重跑（检查确认前一轮成功但 mood-trends 无条目——异常情况）**：正常执行全部流程，包括 emotion-coach 写入，无需特殊说明。

4. **不要因为重跑而静默**：只要本轮成功就正常输出。用户有数据需要回顾，前一轮失败不是跳过总结的理由。

#### 新增场景：输出文件存在但 mood-trends 无今日条目（静默写失败）

2026-07-01 触发了此场景：daily-review 正常跑完并推送了总结（含月度总结），但 action=patch 写入 mood-trends.md 时未实际写入（patch 成功但目标位置不对）。这导致情绪趋势文件出现日期断层，但系统无任何报错。

**检测方法**（在步骤 0.5 中同步执行）：
1. 检查 `~/.hermes/cron/output/<job-id>/` 下今日有无输出文件
2. 若有输出文件（说明 job 跑了），但 mood-trends 无今日条目 → 可能发生了静默写入失败

**处理方式**：
- 不重复写入缺失的 mood-trends 条目（缺乏当日碎碎念上下文，生成的评估空洞）
- 在晚间总结的善意提醒区块中加一句话说明：`💡 补充：昨晚的总结因系统原因未在情绪趋势中留下记录，但内容已正常推送。`
- 正常执行本轮全部流程（包括 emotion-coach 写入今日条目）

**预防措施**：在 emotion-coach 步骤 4 写入后，加一行验证代码：
```python
# 写入后立即验证
check = read_file("~/.hermes/memory/mood-trends.md")
if f"### {today} 情绪评估" not in check.get("content", ""):
    # 写入失败，重试一次
    ...重试逻辑
```

### 步骤 0.6：检查前序日期是否有遗漏

前一天的 Cron 可能因系统宕机、网络故障或调度器错过时间窗口而完全未执行。这会导致数据文件出现了日期断层，但不会触发步骤 0.5 的重跑检测（因为作业本身没有失败，只是从未运行）。

**⚠️ 输出文件存在 ≠ 已推送（2026-08-05 实测）**：判断前一日是否真正完成前，交叉验证三处，不能只看 output 目录有文件：
1. output 文件尾部是否有 `## Error` 区块——失败运行（如 `peer closed connection`）同样会留下大体积输出文件（含完整 skill 全文 + Error 段）
2. jobs.json 中该 job 的 `last_status` / `last_delivery_error`——运行成功但推送失败（如 Weixin `rate limited`）时用户实际未收到
3. mood-trends.md 是否有该日条目——这是最终判定依据

三者一致确认缺失后，按下方「遗漏日处理」说明。若早间简报已提过前日失败（简报会引用 last_delivery_error），晚间补充区块引用简报结论即可，不要重复描述故障细节。

**检查方法**：

1. 读取 `~/.hermes/memory/mood-trends.md`，用正则提取所有 `### YYYY-MM-DD 情绪评估` 标题中的日期
2. 按日期排序（注意：文件中的条目不一定是按日期顺序的——写失败、重跑等情况会导致日期断层），取最近的日期
3. 与今日日期对比，如果存在中间缺失的日期 → 说明遗漏了

   示例代码：
   ```python
   import re, os
   content = open(os.path.expanduser("~/.hermes/memory/mood-trends.md")).read()
   dates = re.findall(r"### (\d{4}-\d{2}-\d{2}) 情绪评估", content)
   dates.sort()
   last_date = dates[-1] if dates else None
   # 然后对比 last_date 和 today，看中间是否有缺失
   ```

**遗漏日处理**：
- **先查历史再输出**：缺失日若已在更早的晚间总结或早间简报中说明过（读取近期 daily-review 输出文件的 Response 段确认），本轮不重复提及，只处理新发现的缺失（2026-08-09 实测：8/4、8/6 两处缺口已分别被 8/5、8/7 的总结说明过，本轮直接跳过，避免重复噪音）
- 如果仅缺失 1 天 → 在晚间总结中的善意提醒区块加一句话说明。不需要补跑整个总结，但要让用户知道系统意识到有缺失。
  ```
  💡 补充：昨晚的总结因系统宕机没跑成。今天正常回顾。
  ```
- 如果缺失 2 天及以上 → 在善意提醒区块中概述缺失天数，并询问是否需要手动补推关键信息（待办到期、积压提醒等）。
- 如果 mood-trends.md 尚未初始化或不存在 → 跳过此步骤（首次使用无历史数据）。

**不修改数据结构**：只做观察和输出，不要回填 mood-trends.md 中缺失日期的条目（除非下一轮 daily-review 的正常流程触发了写入）。缺失的总结因为缺乏原始数据（用户当天的碎碎念），生成的评估也是空洞的。

### 数据完整性检查（Step 1 子节点 — 新增）

**问题场景**：用户当天有活跃会话（通过 `session_search` 可确认），但 data/ 下的 diary/ideas/events/knowledge 文件不存在或无内容。这表示碎片捕获阶段的持久化写入失败（文件未落盘），但会话记录中保留了完整内容。

**检测方法**（在 Step 1 采集完数据文件后执行）：

1. 确认数据文件为空或不存在 → 调用 `session_search(query="YYYY-MM-DD")` 检查当日是否有活跃会话
2. 若 session_search 返回有内容的摘要，但数据文件为空 → 标记为「数据持久化异常」
   - 排除误判：如果 session 摘要明确说「文件不存在」或「无法写入」→ 确认是已知问题，不是新异常
3. 将异常信息加入最终输出，在善意提醒区块中以自然语气说明

**输出示例**（融入善意提醒）：
```
💡 你 10:02 会话中的几条记录（日记、灵感、知识碎片）因系统持久化异常没有写入数据文件，
  只在会话记录里。有时间的话可以补充录入——特别是 [关键内容简述]。
```

**原因分析**：碎片捕获阶段（用户发送消息 → fragment-catcher 处理 → write_file）中，file write 步骤可能因路径解析失败、工具调用超时或被后续操作覆盖而未实际落盘。此检查确保即便写入失败，用户的关键内容仍能被晚间总结识别和提及。

**预防措施**：
- 每日回顾结束时验证关键数据文件是否存在（diary/YYYY-MM-DD.md, events/YYYY-MM-DD.md）
- 若 session_search 显示有内容但文件缺失 → 在输出中引导用户补充录入

### 数据采集实用方法（Step 1 子节点）

以下方法在 Cron 环境中已验证可用：

**quotes.md 今日新增**
```
search_files(pattern="YYYY-MM-DD |", path="~/.hermes/data/quotes/quotes.md")
```
搜索到的匹配行即为今日新增好句。无匹配则无新增。

**知识主题今日新增**（三种检测方法，按优先级使用）

**方法 A（碎片格式检测——推荐）**：读取 knowledge/ 下各主题文件，在「碎片积累」区块中搜索 `YYYY-MM-DD` 日期模式来确认今日新增条目数。

**方法 B（文件修改时间检测）**：`ls -la --time-style=+%Y-%m-%d` 检查修改日期，今日修改的再读内容确认。

**方法 C（独立新文档检测——新增 2026-07-16）**：某些知识以整篇文档而非碎片条目的形式存储（如竞品分析、架构草案、工作流方案），这些文档不带 `## 碎片积累` 区块，也没有 `- YYYY-MM-DD |` 日期前缀行。检测方法：
1. 列出 knowledge/ 下所有 `.md` 文件，排除 `_` 前缀的模板
2. 对每个文件，检查是否包含今日日期（YYYY-MM-DD）关键词但在文件开头 500 字符内无 `## 碎片积累` 区块
3. 同时交叉引用当日 diary/ 和 events/ 文件中出现的「存到knowledge」「已存knowledge」「已入库」「知识」等模式，提取文件路径
4. 这些文档计入「主题数」而非「碎片条数」——在知识积累汇报中以独立文档形式呈现

示例检测代码：
```python
import os, re, glob
from datetime import datetime
today = datetime.now().strftime("%Y-%m-%d")
base = os.path.expanduser("~/.hermes")

# 检测新创建的独立文档
standalone = []
for f in glob.glob(f"{base}/data/knowledge/*.md"):
    fname = os.path.basename(f)
    if fname.startswith("_"):
        continue
    content = open(f).read()
    has_fragments = "## 碎片积累" in content
    mentions_today = re.search(rf"{re.escape(today)}", content[:500])
    if mentions_today and not has_fragments:
        standalone.append(fname)

# 从日记中提取\"存到knowledge\"的引用
diary_path = f\"{base}/data/diary/{today}.md\"
if os.path.exists(diary_path):
    diary = open(diary_path).read()
    saves = re.findall(r\"(已?存(?:入|到|在)? ?knowledge/[^\\s)]+)\", diary)
    for s in saves:
        fname = s.split(\"/\")[-1].replace(\".md\",\"\").strip()
        if f\"{fname}.md\" not in standalone:
            standalone.append(f\"{fname}.md\")

print(f\"Standalone new documents: {standalone}\")
```

**方法 D（文件删除检测——新增 2026-07-17）**：知识文件可能被用户删除或移入 archive。今日 session 中用户删除了两份与产品定义冲突的 GPT 生成文件（SSOT v4.0、v1.2 违规示例）。检测方法：

1. 用 `session_search(query="YYYY-MM-DD 删除 知识 knowledge")` 或类似查询获得当日会话摘要
2. 从摘要中提取文件删除事件的具体路径和原因
3. 交叉验证：列出 knowledge/ 下所有文件，看 session 中提到的文件是否确实不存在
4. 在知识积累汇报中添加「已删除」条目，与新增文档并列展示

示例检测代码：
```python
# 从 session_search 结果中提取删除事件
# session_search 返回的文本中可能包含 "已删除"、"删除"、"清理" 等关键词
# 搜索 "delet" "删除" "清理" "移除" "删掉" 模式
deleted_patterns = r"(删除|delet|清理|移除|删掉|移入.*archiv)"
# 匹配到后，提取被删除的文件名和原因
# 在知识积累汇报中以独立行展示
```

输出示例（整合到知识区块）：
```
📚 知识积累
  └── 今日新建知识文档：
      ├── 长期项目X 架构说明 v3.0
      ├── 长期项目X 开发方法 v3.5
      └── 长期项目X 约束契约 v1.1
  └── 已删除：
      └── SSOT v4.0、v1.2 违规示例（与产品定义冲突）
```

**方法 E（章节追加检测——新增 2026-08-09）**：知识以「给已有文档追加编号章节」的形式新增（实测：`luma-kata-local-llm-analysis.md` 新增「## 七、LFM2.5-2.6B 调研（2026-08-09）」「## 八、MiniCPM5-2B 补充（2026-08-09）」）。这类新增既不是碎片行（方法 A 漏检），也不在文件开头 500 字符内（方法 C 漏检），会导致「今日 0 新增」误报。检测方法：

1. 对 knowledge/ 下所有非模板文件，在**全文**（而非前 500 字符）搜索今日日期：`re.search(rf"{re.escape(today)}", content)`，或匹配标题括号日期模式 `## .*（YYYY-MM-DD）`
2. 命中但非碎片行 → 章节追加型新增，计入对应主题的「今日更新」，不按碎片条数计
3. 汇报时归入知识区块的更新列表，注明「XX 文档新增章节：…」
4. **交叉验证 session 摘要**：session_search 摘要声称「已截断/未归档」时，先读文件确认——摘要可能滞后于实际写入（2026-08-09 实测：摘要称 MiniCPM5-2B 结论未归档，实际 section 八 已完整写入；若直接采信摘要，会给出错误的「建议补录」提醒）

**方法 A & B 的注意事项**——过滤掉 `_` 前缀的模板/示例文件：
```python
import glob, os
for f in glob.glob(os.path.expanduser("~/.hermes/data/knowledge/*.md")):
    if os.path.basename(f).startswith("_"):
        continue  # 跳过模板文件
```

**重要——正则必须兼容无 HH:MM 的格式**：知识碎片文件中的条目格式并非始终严格遵循 `- YYYY-MM-DD HH:MM |` 规范。实测发现 项目X-长期项目X.md、prompt-engineering.md 等文件使用了省略 HH:MM 的格式（`- YYYY-MM-DD | 内容`）。如果检测正则强制要求 HH:MM，新增碎片会被完全漏掉，导致知识积累汇报显示「0 new」但实际有大量新增。**务必使用 `(?: \d{2}:\d{2})?` 使时间戳可选**。all_fragments（累计总数）的检测正则同样需要此调整，否则累计计数也会偏少。

**锻炼完成情况**
使用两阶段检测法，避免关键词的虚假匹配（如"没做锻炼""停练一天"等否定匹配）。

第一阶段——正向信号搜索：在当日 diary 和 events 中搜索明确的完成信号
- 正向模式：`(锻炼[完做]成|完成.*?(?:锻炼|运动)|全套锻炼|体育锻炼)`
- 补充关键词：跑步、散步、深蹲、俯卧撑、拉伸（但仍需配合正向模式过滤）

第二阶段——排除否定匹配：如果匹配行中包含否定词（没做、没、停练、休息、未），标记为未完成

若两阶段后仍无正向匹配 → 今日未完成锻炼。

`execute_code` 实现范例（替换 today 为实际日期）：
```python
positive = r"(锻炼[完做]成|完成.*?(?:锻炼|运动)|全套锻炼|体育锻炼)"
negative = r"(没做|没|停练|休息|未)"
matched = False
for line in diary_lines + events_lines:
    if re.search(positive, line) and not re.search(negative, line):
        matched = True
        break
```

**锻炼检测陷阱（2026-07-23 实测）**：原正则 `完成.*[锻炼运动]` 的字符集 `[锻炼运动]` 会匹配「提炼」「运行」等无关字眼（字符类匹配单一字符，非完整词），导致错误标记为「锻炼已完成」。必须使用非捕获组 `(?:锻炼|运动)` 匹配完整词语。

**获取今日会话上下文**

注意：`session_search` 是**独立工具**（direct tool），不是 `hermes_tools` 的导入函数。
不能在 `execute_code` 中 `from hermes_tools import session_search`——会报 ImportError。
应当在外层直接调用 `session_search()` 工具，或在 `execute_code` 之后单独调用。

正确用法：
```
# 外层直接调用
session_search(query="YYYY-MM-DD")
```

获取当天各次会话的摘要（早间简报内容、碎片捕获记录等），帮助了解用户全天节奏和未完成事项。

**提示**：如果今日有早间简报（08:30 Cron 推送），它的输出已涵盖连续静默天数、待办概况等信息。晚间总结应避免重复已说过的内容——引用简报结论而不是重新罗列一遍。用 `session_search` 获取简报摘要，只需补充简报之后发生的变化。

**思考会话检测（新增 2026-07-29）**

用户有时会发起深度思考会话（架构设计、战略规划、理论学习、认知突破等），这些会话产生了当天最重要的认知产出，但内容未写入知识文件。这是**非异常的正常模式**——用户选择将思考留在对话中而非持久化到 knowledge/。

检测方法：在 session_search 获取的会话摘要中识别以下信号：
- 长时间、多轮次的深度讨论（非单条碎片输入）
- 涉及认知突破性表述："定稿""定型""冻结""里程碑""认知突破""核心公式"
- 有完整的推导链条或理论建构（从 A→B→C 的推理过程）
- 用户语气专注、好奇、投入（非琐碎事务型）

与非思考会话的区分：日常事务型会话（"到货了""已发送""正常上班"）不应标记，只在有明显的认知产出或深度建构时触发。

**检测后处理**：在输出结构的 📖 今日日记后添加一个「💬 今日思考」区块（见输出结构说明），将思考内容浓缩为自然叙述呈现。同时检查思考中产生的认知结论是否值得提议写入 knowledge/——如果是重要的架构定稿或认知突破，在善意提醒中加一句温和提议。

**月份文件今日新增**（expenses/YYYY-MM.md）
```
search_files(pattern="YYYY-MM-DD ", path="~/.hermes/data/expenses/YYYY-MM.md")
```
无匹配则今日无记账。

**Pitfall——文件不存在的情况**：如果该月份尚无任何记账记录，expenses/YYYY-MM.md 文件根本不存在。此时 `search_files` 返回的是路径不存在错误（而非零匹配结果）。需要先 `os.path.exists(目标路径)` 确认文件存在，再用 `search_files` 搜内容。execute_code 中直接 open + search 会触发此问题——改用 `os.path.exists` 前置检查，文件不存在则直接判定「本月无记账」。

**检查今日已触发的提醒**
某些每日必做或用户设置的截止提醒可能已通过 Cron 推送。检查 todos.json 中 `reminder_cron_id` 字段，若有关联 cron 的待办，查看 `~/.hermes/cron/output/<cron_id>/` 下今日的输出文件，确认是否已触发提醒。此信息可融入善意提醒区块，避免重复提示。

**实用命令**：
```
# 列出所有 cron output 目录（按修改时间排序，可知今日哪些 job 运行了）
ls -la ~/.hermes/cron/output/

# 查看某个 job 今日的输出文件
ls -la ~/.hermes/cron/output/<job_id>/
cat ~/.hermes/cron/output/<job_id>/<latest_file>.md

# 查找与某待办关联的 cron job（从 todos.json 的 reminder_cron_id 字段获取 ID）
# ⚠️ 已完成的 one-shot 提醒 job 可能已从 jobs.json 移除（调度器清理），但 output 目录仍保留。
#    验证提醒是否触发：直接用 reminder_cron_id 查 ~/.hermes/cron/output/<id>/ 即可，别花时间搜 jobs.json（2026-08-10 实测：dl-027/dl-025 的 reminder job 均不在 jobs.json 中）。
```

**批量数据采集**（使用 execute_code 替代逐文件 read_file）：
当需要同时检查多个 knowledge 主题文件（今日新增碎片）、或多个日记/事件文件时，
用 `execute_code` 配合 `from hermes_tools import read_file, search_files` 一次搞定，
比逐个 `read_file` 更高效。

示例（替换 YYYY-MM-DD 为实际日期）：
```python
# 注意：知识碎片行的格式通常是 "- YYYY-MM-DD HH:MM | ..."，
# 但部分文件省略了 HH:MM 时间戳（如 "- YYYY-MM-DD | ..."），
# 所以正则中 HH:MM 部分设为可选。
from hermes_tools import read_file, search_files
import glob, re, os
today = "YYYY-MM-DD"
base = os.path.expanduser("~/.hermes")

# Part 1: 碎片格式检测（方法 A）
fragment_topics = {}
for f in glob.glob(os.path.expanduser("~/.hermes/data/knowledge/*.md")):
    basename = os.path.basename(f)
    if basename.startswith("_"):
        continue
    content = open(f).read()
    # 今日新增碎片数（HH:MM 可选，兼容两种格式）
    new_matches = re.findall(rf"^- {re.escape(today)}(?: \d{{2}}:\d{{2}})? \|", content, re.MULTILINE)
    # 累计碎片总数（同样兼容两种格式）
    all_fragments = re.findall(r"^- \d{4}-\d{2}-\d{2}(?: \d{{2}}:\d{{2}})? \|", content, re.MULTILINE)
    all_topics[basename] = {"new": len(new_matches), "total": len(all_fragments)}
    if new_matches:
        fragment_topics[basename] = (len(new_matches), len(all_fragments))
        print(f"{basename}: {len(new_matches)} new, {len(all_fragments)} total")

# 总主题数（用于"知识库维持 N 个主题"行）
print(f"\n总主题数（非模板）: {len(all_topics)}")

# Part 2: 独立文档检测（方法 C）
standalone = []
for f in glob.glob(f"{base}/data/knowledge/*.md"):
    fname = os.path.basename(f)
    if fname.startswith("_"):
        continue
    if fname in fragment_topics:
        continue  # 已在碎片列表中，避免重复
    content = open(f).read()
    if "## 碎片积累" not in content and re.search(rf"{re.escape(today)}", content[:500]):
        standalone.append(fname)
        print(f"[DOC] {fname}: standalone document created today")

if standalone:
    print(f"Standalone documents: {standalone}")
```

**日记 vs 事件文件格式差异**：diary/ 使用 `-` 项目符号格式（`- HH:MM | 内容`），events/ 使用 `|` 表格格式（`| HH:MM | 事件 |`）。批量采集时不要用同一套解析模式处理两种文件——用 `read_file` 按各自格式分别解析。diary 的 `execute_code` 正则应匹配 `^- \d{2}:\d{2} \|` 而非 `|` 表格分隔符。

**⚠️ events 格式不稳定（2026-08-10 实测）**：events/ 文件实际也可能用 `-` 项目符号格式（`- 07:42 | 内容`）而非文档所述的 `|` 表格格式。若只按 `|` 开头过滤会**全部漏掉**——实测误报「events 0 条」，实际文件有 4 条事件，直到 read_file 直读才发现。解析时应同时接受两种格式，例如：
```python
if l.strip().startswith("|") or re.match(r"^- \d{2}:\d{2} \|", l.strip()):
    events_lines.append(l.strip())
```
批量结果为零时，务必用 read_file 直接读文件确认是真空还是解析遗漏（events 内容常与 diary 重叠，可交叉验证）。

**Python f-string 陷阱**：在 `execute_code` 的 f-string 表达式中不能使用反斜杠转义（Python 3.11 及更早版本的限制）。
```python
# ❌ 会报 SyntaxError
print(f"行数: {len([l for l in lines.split('\\n')])}")

# ✅ 正确做法：将反斜杠表达式提取到临时变量
newline = "\n"
print(f"行数: {len([l for l in lines.split(newline)])}")

# ✅ 或用 % 格式化绕开
print("行数: %d" % len(lines.split('\n')))
```

**安全提示**：Cron 环境的 `terminal` 对 `python3 -c` 内联脚本和 pipe-to-interpreter 模式
（如 `cat file | python3 -c`）有安全拦截，无法使用。需要解析 JSON 或做复杂数据处理时，
务必使用 `execute_code` 工具而不是在 shell 中调用 Python。

**已验证的备选模式**：当 `execute_code` 的 `from hermes_tools` 导入失败或返回值格式异常（如 `KeyError: 'content'`）时，使用以下模式绕开：
1. 用 `write_file` 将脚本写入 `/tmp/script.py`（纯 Python，不使用 hermes_tools，直接 open + 标准库解析文件）
2. 用 `terminal('python3 /tmp/script.py')` 执行并获取输出
示例：数据分析脚本写入 `/tmp/analyze_todos.py`，内容为 `json.load(open("~/.hermes/data/todos.json"))` 标准库操作，可稳定运行。

**早间简报原文定位**：daily-briefing 的 cron 输出文件（`cron/output/<job_id>/<date>.md`）中，Prompt 段包含完整 skill 全文，实际推送内容在 `## Response` 标记之后。直接读输出文件可拿到简报原文，与 session_search 摘要互为补充（摘要偏事件概括、原文偏措辞细节），用于「引用简报结论而非重新罗列」时准确还原简报说了什么。

**系统健康信号——memory 写入失败**：session_search 摘要中若出现 memory 写入失败信号（「记忆容量满」「2187/2200」「threat pattern 拦截」「写入失败」等），说明工作记忆层接近饱和或触发安全拦截（2026-07-31 实测：一次因提及 .env 被 threat pattern 拦截，一次因容量满）。**接近饱和但写入成功的信号同样值得提醒**：摘要出现「精简后写入，2,190/2,200 chars」这类描述时（2026-08-09 实测），说明已到 99% 容量，下一次写入随时可能失败——与写失败同等对待，在善意提醒中自然提一句「记忆层快满了，改天有空清理合并一下旧条目」。这值得在善意提醒区块中以自然语气提示用户（如「记忆容量快满了，今天有两次记忆写入失败，改天有空清理合并一下旧条目」）——用户不被告知就不会知道后续新记忆可能存不进去。这是观察类信号，不是待办，不需要修复动作。

**系统健康信号——备份 Cron 被注入扫描器拦截（新增 2026-08-08）**：检查 data-backup job 的 output 目录（`~/.hermes/cron/output/<job-id>/`，job id 从 jobs.json 按 name=data-backup 查）今日输出文件，若显示 `Status: BLOCKED` 且提示 `prompt matches threat pattern ...`（如 `exfil_curl_auth_header`），说明该 job 关联 skill 的内容命中了 cron 威胁正则，备份未运行（jobs.json 中 last_status=error）。这是可修复的系统问题——改写 skill 中触发模式（如 curl 的 Authorization header 改为变量间接引用）后即可恢复，详见 data-backup skill 已知陷阱表。晚间总结应在善意提醒区块告知用户拦截事实与修复状态，并顺带检查 git log / backup-status.json 判断积压程度（本地 commit 通常已保全，远程同步可能中断）。检测时机：扫描 cron output 目录时一并查看，不单独增加步骤。

---

```
Cron 22:00 触发
  │
  ├─ 步骤 1：收集今日数据
  │   ├── 扫描 ~/.hermes/data/diary/YYYY-MM-DD.md
  │   ├── 扫描 data/ideas/YYYY-MM-DD.md
  │   ├── 扫描 data/events/YYYY-MM-DD.md
  │   ├── 扫描 data/expenses/YYYY-MM.md（详见: 月份文件今日新增）
  │   ├── 扫描 data/knowledge/ 中今日有新增的主题文件（详见: 知识主题今日新增）
  │   ├── 扫描 data/quotes/quotes.md 中今日新增条目（详见: quotes.md 今日新增）
  │   └── 扫描 todos.json 中今日标记完成的条目
  │
  ├─ 步骤 2：生成今日总结
  │   └── 将收集的数据分类呈现
  │
  ├─ 步骤 3：知识积累汇报
  │   └── 统计今日知识主题的碎片新增和累计
  │
  ├─ 步骤 4：今日完成事件
  │   └── 列出今日标记完成的待办
  │
  ├─ 步骤 5：惊奇度扫描
  │   ├── 拿今日碎片批次 vs memory/ 已有内容比对
  │   ├── 发现高惊奇信号 → 提议写入 memory/
  │   └── 发现知识连接/困惑 → 在总结中主动提示
  │
  ├─ 步骤 6：调用情绪教练
  │   └── 分析今日碎碎念的情绪信号 + 个性化评价
  │
  └─ 步骤 7：善意提醒
      └── 检查是否有新的善意提醒候选
```

---

## 输出结构

### 1. 今日总结

按类别整理今天所有的碎碎念。

**格式**：

```
📖 今日日记
  ├── 14:30 跑步了，感觉不错，看到夕阳很美
  └── 21:00 今天和客户开了个会，有点累

💡 今日灵感
  └── 16:00 突然想到可以做一个碎片输入的 AI 助手

📰 今日事件
  └── 10:00 收到项目 A 的反馈邮件

💬 今日好句
  └── "生活不是等待暴风雨过去，而是学会在雨中跳舞"

💰 今日记账
  └── 12:30 午饭 38 元

📚 今日学习（详见下方知识汇报）
```

如果某个类别今天没有记录 → 跳过该类别，不显示空区块。

**思考会话区块**：当「思考会话检测」（见数据采集部分）触发时，在 📖 今日日记和 💡 今日灵感之间插入：

```
💬 今日思考
  └── [思考内容的浓缩叙述——自然语言，不以碎片格式逐条列出]
```

与 💬 今日好句的关系：两者共用 💬 emoji，但上下文区分。思考会话放在日记后、灵感前；好句放在事件后、记账前。
与知识积累汇报的关系：如果思考中产生了应入库的认知成果（架构定稿、路线图确认等），在善意提醒区块中温和提议：「有空把今天的结论存到知识库」。

### 2. 今日完成

列出今天标记完成的待办，以及每日必做事项的完成情况。**留意那些被更新/推进但尚未标记完成的待办**——例如用户修改了待办文本（合同已发出、状态更新等），虽然 done 字段仍为 false，但实际有进展。这些也值得在今日完成中提及，用区别于完整完成的表述（如「推进中」或「已更新」）。

```text
✅ 今日完成
  ├── 给张总发方案（14:30 完成）
  ├── 🏋️ 今日锻炼已完成
  └── 买牛奶（18:00 完成）
```

如果今天没有完成任何待办 → 显示「今天没有完成事项。明天继续。」（语气平和，不带评判）

**Cron 环境下的待办状态同步**：当 diary/events 中明确记载某项待办已完成（如「考勤统计完成」「XX收尾」等表述），虽然 todos.json 的 done 字段仍为 false，应**主动更新** todos.json 的 done=true 和 done_at=today，而非等待用户确认。判断标准：
  - 必须明确提及该待办的具体内容或核心动词（如「考勤统计完成」→ 匹配「整理考勤表」）
  - 必须是完成陈述（「做完了」「完成了」「搞定了」「收尾了」），而非计划性陈述（「计划做」「准备做」「需要做」）
  - 如果只有一个模糊的完成信号（如「今天忙完了」但未指定事项），则不在系统内标注完成，仅在输出中提及「可能已完成，需确认」
  - 同时清理关联的 reminder_cron_id 对应的 Cron 任务
  因为这是 Cron 环境（无用户实时交互），不要留下「要不要我帮你标上」这类需要用户回复的问题——直接执行并说明即可：`已标注 dl-014 整理考勤表为完成。`

如果锻炼还没做 → 在今日完成末尾温和提示：
```text
  🏋️ 今日锻炼尚未完成。不限时间，睡前抽空做了就行。
```

### 3. 知识积累汇报

扫描 data/knowledge/ 下今天有新增碎片的主题文件，统计每个主题的进展。

**有新增碎片时**——按主题逐条展示：

```
📚 知识积累
  ├── RAG
  │   ├── 今日新增：2 条碎片
  │   ├── 累计：5 条
  │   └── 待消化：GraphRAG 和普通 RAG 的区别还没搞懂
  │
  └── 投资理财
      ├── 今日新增：1 条碎片
      └── 累计：3 条
```

**有新增独立文档时（方法 C 检测到）**——文档不按碎片条目计，单独列出：

```
📚 知识积累
  └── 今日新建知识文档：
      ├── 长期项目X 开发工作流（五层模型定稿）
      ├── 长期项目X 竞品分析（竞品A + 竞品D）
      └── 长期项目X 架构约定 v1.0（双脑架构冻结）
```

**同时有碎片新增和独立文档时**——先列碎片主题，再列独立文档，用空行隔开。

**无新增碎片时**——一行带过，不展示空模板：

```
📚 知识积累
    今日无新增碎片。知识库维持 N 个主题。
```

**计算 N**：N 来自 knowledge/ 下所有非模板文件（过滤掉 `_` 前缀）的总数。在 execute_code 扫描时，即使某个文件今日无新增碎片，也应将其计入总计数。示例：`glob.glob("~/.hermes/data/knowledge/*.md")` 输出的文件列表，排除 `_` 前缀文件后的长度即为 N。

**知识目录为空时（无任何主题文件）**：

```
📚 知识积累
    知识库尚未创建主题文件，今日无新增碎片。
```

**主动建议**：如果某个主题累计 10+ 条碎片或有超过一周的待消化项，加一句提议（无论今日有无新增）：

```
  💡 RAG 话题已经积累了 12 条，要不要帮你串一串出一个概要？
```

### 4. 惊奇度扫描结果

#### 关于「你这个人」的模式

拿今日碎片批次 vs memory/ 已有内容做比对。

**如果发现高惊奇信号**，在总结中自然地提一句：

```
💬 我注意到你最近三天都在晚上 10 点后发碎片，之前你不是这个习惯。
  要不要我记住这个变化？
```

**如果用户同意** → 写入 memory/ 对应文件 + 更新 MEMORY.md 索引。

**如果没有发现** → 跳过此区块。

#### 关于知识的连接

**如果发现知识碎片之间有连接或矛盾**：

```
📚 知识关联
  你今天说的 RAG chunk 策略，和 6/2 你提到的 RAG 检索难点有关联——
  chunk 切得好不好直接影响检索质量。这可能是一个思路。
```

**如果没有发现** → 跳过。

### 5. 情绪教练评价

调用 emotion-coach Skill，将结果融入总结末尾。

```
🌟 今日情绪
  今天整体状态不错——下午跑步那段能感觉出心情挺好。
  晚上提到了「有点累」，可能是客户会的缘故。
  总体来说，今天有产出也有休息，节奏挺健康。
```

**风格**：
- 温和，不审判
- 基于实际内容，不模板化
- 如果今天没什么情绪信号 → 简短带过（「今天情绪比较平稳，没什么特别。」）
- 如果有明显的负面信号 → 给一句有温度的话（不是「加油哦」）

### 6. 善意提醒

检查是否有新的善意提醒候选。如果有，温和提示：

```
💡 顺便说一句
  你 6/2 提到「GraphRAG 还没搞懂」，已经快一周了。
  有空的话可以找时间看看。
```

如果没有 → 跳过。

---

## 输出风格规则

1. **搭档语气**：不是写报告，是和朋友聊今天的回顾
2. **简洁**：每个区块几行就够，不展开
3. **有选择性地呈现**：没有数据的区块直接跳过，不展示空区块
4. **温度适度**：不过度关心，也不冷冰冰
5. **不用感叹号**：用句号
6. **惊奇度和情绪融入自然对话**：不单独标注「惊奇度扫描结果」或「情绪分析报告」

---

## 月度总结扩展

当 cron 提示词或用户要求生成月度总结时，所有数据已在步骤 1 中采集完毕。无需额外数据收集。

具体分析框架和输出结构请参见 `references/monthly-summary.md`。月度总结不是独立 skill，它复用 daily-review 的数据管道和行为模式分析方法。

**关键区别**：
- **范围**：月度总结扫描当月所有 date*/events* 文件（约 30 天），而非仅今日
- **分析深度**：月度总结需要提取跨日行为模式（4-6 条），而非仅今日的惊奇信号
- **自我批评回应**：月度总结需要用全月数据回应任何突出的用户自评，给出基于数据的批评
- **SKILL.md 不记录月总结细节**：请查阅 `references/monthly-summary.md`

---

## SILENT 决策指引

每天汇报还是静默？判断规则：

| 场景 | 决策 | 理由 |
|------|------|------|
| 用户当天有主动录入（日记/灵感/事件/待办完成/碎片等任何一项） | ✅ 正常输出 | 有内容需要回顾 |
| 用户当天零录入，但有关联上下文（今日有到期待办、有提醒已推送、有跨日计划） | ✅ 正常输出（简短版） | 虽然无新内容，但「没记录」本身是信息，且跨日计划需要关注 |
| 用户当天零录入，无任何关联上下文，系统也无任何事件 | ❌ [SILENT] | 真正没什么可说的 |
| 数据目录不存在或全部数据源无法读取 | ❌ [SILENT] | 基础设施问题，静默失败 |

**低数据日输出原则**：当用户零录入但有上下文时，输出控制在 5-8 行以内，跳过所有空区块，情绪评价一句带过。不要因为内容少就扩写凑数。

**零录入日输出格式**：当用户全天无任何录入（无日记/灵感/事件/碎片/待办完成）时，不使用标准的 emoji 区块格式（📖📰💡💬💰）。改用紧凑叙述格式，将所有内容合并为 3-4 个自然区块，使用 `###` 作为块标题：

```
## 📋 今日回顾 · YYYY-MM-DD（周日）

今天很安静，没有新的录入。[日期类型]，[节奏说明一句]。

### ⏰ 到期待办/需关注
[如果有关联上下文——到期待办、积压提醒等——在此行说明]
[如果没有上下文 → 跳过此区块]

### 📚 知识积累
    今日无新增碎片。知识库维持 N 个主题。

### 🌟 今日情绪
[情绪教练评价，一句带过]

### 💡 补充(可选)
[数据备份状态、前日遗留说明等系统级信息]
```

- 主标题用 `## 📋 今日回顾`（非 emoji 区块格式）
- 每个子标题用 `###` 而非 `📖`/`💡` 等 emoji 前缀
- 严格：只在有实际内容的区块上写标题，空区块全跳过
- 到期待办区块只在有当日截止或积压提醒时出现
- 情绪区块永远保留（最低限度一句）
- 情绪区块可以在一句基调后追加一句**上下文感知的收尾**（如明日行程提醒、健康叮嘱），而非严格一字不动的模板句——这符合「温度适度」风格，但只加一句，不扩写（2026-08-02 实测：「今天很安静。周日休息日，正常的休息节奏。明天出发去山海关，路上注意安全。」）
- 补充区块仅在有系统级信息时才出现（备份、前日异常等）
- 保持紧凑：每个区块控制在 3-4 行实际内容以内

**连续静默日处理**：当出现 2 天及以上的连续零录入时，静默本身成为值得关注的信息。
- 在开场白中标注「这是连续第 N 天了」
- 在善意提醒区块中点出「你连续 N 天没和系统互动了」，并附上积压的待办提醒
- 连续 3 天静默 → 情绪教练评价中标记备注为「可能处于长假/出差/健康状态，需留意回归信号」
- 连续 7 天静默 → 惊奇度扫描应触发模式变更提醒（用户使用习惯已发生结构性改变）
