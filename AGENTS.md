---
title: AGENTS.md
type: system-core
description: 工作空间说明书——目录结构、数据格式、操作约定、敏感规则。
version: 3.0
created: 2026-05-31
updated: 2026-08-17
---

# AGENTS.md

Agent 的工作空间说明书。告诉 AI：工作空间长什么样、数据什么格式、什么能做什么不能做。

> 本文件不包含人格定义（那是 SOUL.md）、不包含记忆（那是 MEMORY.md）、不包含执行逻辑（那是 Skill）。
> 只写结构、格式、规则。

---

## 工作空间结构

```
~/.hermes/                          ← Hermes HOME 目录
├── SOUL.md                         ← AI 人格（不在本文件管辖范围）
├── USER.md                         ← 用户档案（不在本文件管辖范围）
├── MEMORY.md                       ← 记忆索引（约 2200 字符，指向 memory/）
├── AGENTS.md                       ← 本文件
│
├── memory/                         ← 详细记忆存储
│   ├── preferences.md              ← 用户偏好（由惊奇度扫描写入）
│   ├── patterns.md                 ← 行为规律（由惊奇度扫描写入）
│   └── mood-trends.md              ← 情绪趋势（由每晚情绪教练追加）
│
├── data/                           ← 用户个人数据
│   ├── todos.json                  ← 三类待办（见下方数据格式）
│   ├── projects/                   ← 大项目文件（每个项目一个 .md）
│   ├── diary/                      ← 日记（文件名格式：YYYY-MM-DD.md）
│   ├── ideas/                      ← 灵感库（文件名格式：YYYY-MM-DD.md）
│   ├── quotes/                     ← 好言好句（追加到 quotes.md）
│   ├── expenses/                   ← 记账（文件名格式：YYYY-MM.md）
│   ├── events/                     ← 事件记录（文件名格式：YYYY-MM-DD.md）
│   ├── knowledge/                  ← 知识碎片（按主题命名：主题名.md）
│   ├── inbox/                      ← 未分类碎片
│   └── archive/                    ← 已完成/过期归档（只读）
│
├── skills/                         ← 技能目录（按需加载）
│   ├── fragment-catcher/SKILL.md
│   ├── task-manager/SKILL.md
│   ├── reminder-engine/SKILL.md
│   ├── daily-briefing/SKILL.md
│   ├── daily-review/SKILL.md
│   └── emotion-coach/SKILL.md
│
├── cron/                           ← 定时任务（由 Cron 调度器管理）
└── sessions/                       ← 会话历史（SessionDB，不手动修改）
```

---

## 数据格式

### todos.json — 三类待办

```json
{
  "quick_tasks": [
    {
      "id": "qt-NNN",
      "text": "任务内容",
      "created": "ISO8601 时间戳",
      "done": false,
      "tags": ["标签"]
    }
  ],
  "deadlines": [
    {
      "id": "dl-NNN",
      "text": "任务内容",
      "deadline": "ISO8601 时间戳",
      "created": "ISO8601 时间戳",
      "done": false,
      "reminder_cron_id": "Cron 任务 ID 或 null",
      "tags": ["标签"],
      "project": "项目 ID 或 null"
    }
  ],
  "projects": [
    {
      "id": "pj-NNN",
      "name": "项目名称",
      "file": "projects/文件名.md",
      "status": "idea | planned | active | done",
      "progress": 0.0
    }
  ]
}
```

**字段说明**：
- `id`：唯一标识符，格式为类型前缀 + 三位数字（qt-001、dl-001、pj-001）
- `done`：布尔值，完成后设为 true 并记录在 `data/diary/` 当天的日记中
- `reminder_cron_id`：关联的 Cron 任务 ID，任务完成后需同步清理
- `project`：关联的长待办 ID，用于定时待办挂载到项目下

### 大项目文件（data/projects/ 下）

每个项目一个 .md 文件，文件名用英文短横线连接。

```yaml
---
name: 项目名称
status: idea | planned | active | done
priority: high | medium | low
created: YYYY-MM-DD
deadline: YYYY-MM-DD 或 null
tags: [标签列表]
---

## 目标
[项目要达成什么]

## 已完成子项
- YYYY-MM-DD | [子项描述]
- YYYY-MM-DD | [子项描述]

## 备注
[补充说明]
```

**说明**：
- 长待办目前不需要分解和规划功能，保持扁平结构
- 「已完成子项」用于记录用户提及的、属于该项目的完成事件
- status 流转：idea → planned → active → done

### 知识主题文件（data/knowledge/ 下）

每个主题一个 .md 文件，文件名为主题名。

```markdown
# [主题名]

## 碎片积累
- YYYY-MM-DD HH:MM | [用户口述的知识碎片原文]

## 待消化
- YYYY-MM-DD | [用户表达了困惑但还没理清的内容]

## 连接点
- → [与其他知识或主题的关联]

## 概要
[积累到一定量后可选生成的结构化概要]
```

### 日记文件（data/diary/ 下）

每天一个文件，文件名 `YYYY-MM-DD.md`。

```markdown
# YYYY-MM-DD

- HH:MM | [日记内容]
- HH:MM | [日记内容]
```

### 灵感文件（data/ideas/ 下）

每天一个文件，文件名 `YYYY-MM-DD.md`。

```markdown
# YYYY-MM-DD 灵感

- HH:MM | [灵感内容]
- HH:MM | [灵感内容]
```

### 好句文件（data/quotes/）

追加到一个文件 `quotes.md` 中。

```markdown
# 好言好句

- YYYY-MM-DD | [好句原文]
- YYYY-MM-DD | [好句原文]
```

### 记账文件（data/expenses/ 下）

每月一个文件，文件名 `YYYY-MM.md`。

```markdown
# YYYY-MM 记账

- YYYY-MM-DD HH:MM | [金额] [描述]
- YYYY-MM-DD HH:MM | [金额] [描述]
```

### 事件文件（data/events/ 下）

每天一个文件，文件名 `YYYY-MM-DD.md`。

```markdown
# YYYY-MM-DD 事件

- HH:MM | [事件描述]
- HH:MM | [事件描述]
```

### memory/ 条目格式

每个记忆文件中的条目格式统一为：

```markdown
### [简短标题]
- **强度**：★ | ★★ | ★★★
- **发现日期**：YYYY-MM-DD
- **证据**：[具体行为或对话记录的简述]
- **related**：[关联的其他记忆条目]
- **备注**：[补充说明]
```

### MEMORY.md 索引格式

```markdown
### 类别（强度）
- 简短描述 → memory/文件名.md
```

---

## 操作约定

### 碎片处理

1. 收到碎片 → 意图识别 → 分入 8 类之一
2. 根据类型路由到对应存储位置
3. 如果是待办类，进一步判断属于哪一类（长待办/常规/定时）
4. 如果是知识类，提取主题并追加到对应主题文件
5. 如果有提醒意图，自动创建 Cron 任务
6. 一句话确认回复用户

### 待办管理

- **创建**：根据碎片内容自动分类，写入 todos.json 对应数组
- **查询**：触发词「有什么事」「待办」「计划」→ 从 todos.json 读取并格式化展示
- **完成**：用户说「做完了」「发了」「搞定了」等 → 更新 todos.json done 字段 → 清理关联 Cron
- **归档**：已完成项目 → 移入 data/archive/

### 提醒管理

- 有明确截止时间 → 自动创建 Cron，按 USER.md 提醒偏好配置
- Cron 创建后记录 reminder_cron_id 到 todos.json
- 任务完成后同步清理对应 Cron

### 知识积累

- 新碎片提取主题 → 查 knowledge/ 下有无匹配文件
- 有匹配 → 追加到「碎片积累」区块
- 无匹配 → 新建主题文件
- 识别到困惑信号 → 追加到「待消化」区块
- 识别到关联信号 → 追加到「连接点」区块

### 记忆管理

- 晚间惊奇度扫描发现新模式 → 提议写入 memory/
- 用户确认 → 写入 memory/ 对应文件 + 更新 MEMORY.md 索引
- ★★★ 级别 + 用户确认 → 毕业到 USER.md，原条目标注 `[已毕业]`

---

## 敏感数据规则

| 数据类型 | 修改规则 |
|---------|---------|
| USER.md | 需用户逐条确认 |
| memory/ 下所有文件 | 需用户确认（毕业条目除外） |
| SOUL.md | 需用户明确同意 |
| data/ 下用户输入的碎片 | 不主动修改（存档即定稿） |
| data/archive/ | 绝对不修改 |
| todos.json | 待办增删改可自主操作；项目新建需确认 |

---

*MyPS v3.0 · 2026-08-17*
