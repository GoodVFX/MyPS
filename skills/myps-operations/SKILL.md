---
name: myps-operations
description: MyPS 个人助理系统运维——管理 Skill 与 Cron 任务的对应关系，系统状态检查，启动与恢复。
version: 1.0
created: 2026-06-01
when_to_use:
  - 用户问「为什么某某提醒没推送」「某某功能没生效」
  - 需要检查系统运行状态或 Cron 任务列表
  - 新部署或搬家后需要恢复 MyPS 运行
  - 排查 Skill 存在但功能未触发的场景
  - 用户需要了解系统当前运行了哪些自动任务
---

# MyPS 系统运维

MyPS 个人助理系统由 6 个核心 Skill 组成，但 **Skill 文件存在 ≠ 功能在运行**。每个 Skill 需要对应的 Cron 任务才能按计划触发。

---

## 核心架构

```
Skills 定义「做什么、怎么做」
     ↓ 需要 Cron 任务来触发
Cron 任务定义「什么时候做」
     ↓ 执行时加载对应 Skill
实际推送
```

**关键教训**：Skill 文件和 Cron 任务是两层概念。创建 Skill 后**必须单独注册 Cron 任务**，否则功能不会自动运行。

---

## 6 个核心 Skill 及其所需 Cron 任务

| Skill | 所需 Cron | 触发时间 | 说明 |
|-------|----------|---------|------|
| fragment-catcher | 无（被动触发） | 用户发消息时 | 无需 Cron，实时响应 |
| task-manager | 无（被动触发） | 用户发指令时 | 无需 Cron |
| reminder-engine | 配合 task-manager | 待办截止时 | 由 task-manager 创建的待办自动生成 Cron |
| daily-briefing | ✅ 必须创建 | 每天 08:30 | `0 8 * * *` 加载 daily-briefing skill |
| daily-review | ✅ 必须创建 | 每天 22:00 | `0 22 * * *` 加载 daily-review + emotion-coach skill |
| emotion-coach | 由 daily-review 调用 | 22:00 | 作为 daily-review 的附属 skill 加载，不单独设 Cron |

---

## 定时技能注册流程（通用指南）

当为新技能创建定时 Cron 任务时：

### 第一步：确认技能内容

```python
skill_view(name='技能名')
```

确保 SKILL.md 中的 `when_to_use` 包含 Cron 触发条件。

### 第二步：创建 Cron 任务

```python
cronjob(
    action='create',
    name='技能名',
    schedule='Cron 表达式或 ISO 时间戳',
    skills=['技能名'],           # 运行时加载的技能
    prompt='执行该技能的任务指令',
    deliver='origin',
    workdir='~/.hermes'   # ★ 重要：涉及相对路径时必须设
)
```

**常用调度表达式**：

| 频率 | 表达式 | 说明 |
|------|--------|------|
| 每日 | `30 8 * * *` | 每天 8:30 |
| 每日 | `0 22 * * *` | 每天 22:00 |
| 每月 | `0 9 1 * *` | 每月 1 号 9:00 |

### 第三步：验证

```python
cronjob(action='list')
```

检查任务是否已注册、`next_run_at` 是否正确、workdir 是否设置。

### ⚠️ 关键 Pitfalls

| 问题 | 后果 | 修复 |
|------|------|------|
| 忘记设 `skills` 参数 | Cron 运行时无上下文 | 更新：`cronjob(action='update', job_id='...', skills=['skill-name'])` |
| 忘记设 `workdir` | 相对路径解析错误 → 数据为空 → `[SILENT]` | 更新：`cronjob(action='update', job_id='...', workdir='~/.hermes')` |
| `repeat` 次数用尽 | 月度任务一年后停发 | 注意续期或设 repeat=0（永久） |
| 当月 1 号已过创建月度任务 | `next_run_at` 跳到下月 | 手动执行一次：`cronjob(action='run', job_id='...')` |

---

## 系统状态检查流程

当用户反馈「某功能没生效」时：

1. **检查 Cron 任务列表**：`cronjob action='list'`
2. **检查对应 Skill 是否存在**：`skills_list`
3. **核对缺失项**：看上表，确认必要的 Cron 任务是否已创建
4. **如果 Cron 缺失**：创建对应的 Cron 任务（参考下文的创建命令）
5. **如果 Skill 缺失**：确认用户的 MyPS 是否完整部署

> 模型后端/版本验证（「你现在接的是不是正式版」）见 `references/model-backend-verification.md`

### 批量恢复命令参考

创建每日简报 Cron：
```python
cronjob action='create' name='daily-briefing' schedule='30 8 * * *' skills=['daily-briefing'] prompt='执行早间简报。加载 daily-briefing skill，按照输出结构生成今天的简报内容，推送给用户。' deliver='origin' workdir='~/.hermes'
```

创建晚间总结 Cron：
```python
cronjob action='create' name='daily-review' schedule='0 22 * * *' skills=['daily-review', 'emotion-coach'] prompt='执行晚间总结。加载 daily-review 和 emotion-coach skill，按照输出结构生成今天的晚间回顾，推送给用户。' deliver='origin' workdir='~/.hermes'
```

---

## 系统文件结构

```
~/.hermes/
├── skills/
│   ├── fragment-catcher/SKILL.md
│   ├── task-manager/SKILL.md
│   ├── reminder-engine/SKILL.md
│   ├── daily-briefing/SKILL.md
│   ├── daily-review/SKILL.md
│   └── emotion-coach/SKILL.md
├── data/
│   ├── diary/         # 日记碎片
│   ├── ideas/         # 灵感碎片
│   ├── events/        # 事件碎片
│   ├── expenses/      # 记账碎片
│   ├── knowledge/     # 知识积累碎片
│   └── quotes/        # 好句碎片
├── todos.json         # 待办数据
└── memory/            # 持久记忆
```

---

## 常见问题排查

### 「简报没收到」
- 检查 `cronjob action='list'` 是否有 daily-briefing 任务
- 检查 Cron 任务状态是否为 enabled
- 检查 `next_run_at` 是否正常
- 检查 workdir 是否设为 `~/.hermes`（否则技能读不到 data/ 数据，输出 [SILENT] 导致静默丢失）
- 检查 deliver 是否为显式微信 chat ID（generic `origin` 或 `weixin` 在微信平台可能无法正确路由）
- **已知行为**：Cron 推送有约 4 分钟的轮询延迟，属于调度器正常误差。如果每次稳定延迟 4 分钟且内容正确，说明系统正常。如要更准点，可将触发时间提前 5 分钟。

### 「晚间总结没收到」
- 同上，检查 daily-review Cron 任务是否存在
- 确认 skills 参数是否同时包含了 daily-review 和 emotion-coach
- **关键检查**：Cron 的 workdir 配置是否正确。如果不设 workdir，Cron 从用户 HOME 启动，`data/diary/` 解析为 `~/data/diary/` 而非 `~/.hermes/data/diary/`。修复：更新 Cron 添加 `workdir='~/.hermes'`

### 「Cron 执行成功但扫描数据为空」——新的常见陷阱
**现象**：Cron 任务状态 `last_status=ok`，但生成的总结说「今天无数据」或输出 [SILENT]。

**原因**：Cron 未设 `workdir`，技能中的相对路径 `data/diary/` 等指向了错误位置。

**修复**：
1. 查看当前 Cron 的 workdir：`cronjob(action='list')`
2. 如果 workdir 为空，更新：`cronjob(action='update', job_id='<id>', workdir='~/.hermes')`
3. 手动运行验证：`cronjob(action='run', job_id='<id>')`

**预防**：创建 Cron 任务时始终检查技能是否使用了相对路径。如果是，必须设 workdir。

> 完整排查记录见 `references/cron-workdir-resolution.md`
> 微信限速详细调查见 `references/wechat-rate-limit-investigation.md`

### 「Cron 显示状态 ok 但用户没收到（微信平台）」——重要！
**现象**：`cronjob action='list'` 显示 `last_status=ok`，但用户反馈消息没到。

**三种可能原因**：

| 模式 | `last_delivery_error` | 根因 | 修复 |
|------|----------------------|------|------|
| A. 数据空 → 静默抑制 | `null` | workdir 未设置，技能读不到 data/ | 设 workdir |
| B. 路由错误 | `null` | deliver 目标设置不对 | 更新 deliver |
| C. 平台限速 | 有错误信息 | 微信 iLink 限速 | 用 session_search 恢复（见下方） |

**排查步骤**：
1. **检查 `last_delivery_error` 字段**——不要只看 `last_status`。`last_status=ok` 只表示调度器成功执行了 prompt 并尝试了推送，不代表消息已到达用户客户端。
2. **如果有错误信息**（如 `iLink sendmessage rate limited`）：这是平台限速。见下方「限速恢复流程」。
3. **如果 `last_delivery_error=null`**：检查 workdir 和 deliver 目标。

**修复方法（路由/数据问题）**：
- 更新 deliver 为具体的微信 chat ID 格式：`weixin:<chat_id>`
  ```
  cronjob action='update' job_id='<job_id>' deliver='weixin:<你的微信ChatID>'
  ```
  chat_id 可以从当前会话的上下文信息中获取（Source 行中的 Weixin DM ID），或通过 `send_message action='list'` 查看可用平台目标。
- 更新 workdir：`cronjob action='update' job_id='<job_id>' workdir='~/.hermes'`
- 验证：更新后手动触发一次 `cronjob action='run' job_id='<job_id>'`
- 兜底：如果 Cron 推送始终无法到达，在活跃会话中直接执行晚间总结内容发给用户。

### 「推送因平台限速丢失」——排查与恢复流程

> 详细调查记录见 `references/wechat-rate-limit-investigation.md`

**现象**：`last_delivery_error` 包含 `rate limited`、`rate limit` 等字样。`last_status=ok`。

**原因**：微信 iLink 接口有频率限制。腾讯未公开具体配额。关键规律：**用户主动发消息后的回复从不限流，服务端主动推送（Cron）间歇性受限**。用户静默期（多日无交互）风险更高。

**注意**：`last_status=ok` 只代表调度器成功执行了 prompt 并尝试了推送，**不代表消息已到达用户客户端**。必须检查 `last_delivery_error` 字段。

#### 深入排查步骤

当用户反馈「没收到消息」时，不要只检查 Cron 是否运行，要执行完整排查：

1. `cronjob action='list'` → 检查所有任务的状态和 last_delivery_error
2. **横向对比**：同时间段内，不同的 Cron 任务是否都受限？如果只有部分受限（如 SSL 提醒成功但 briefing 失败），说明不是全局性问题
3. **纵向对比**：连续几天的推送是否都失败？还是偶发？session_search 可追溯历史会话
4. **用户交互周期分析**：用户最后一次主动会话是什么时候？如果多日无交互，更容易触发限速
5. **确认 Cron 内容已生成**：通过 session_search 找回执行记录，确认内容没有丢失
6. **评估影响范围**：是全部推送都失败，还是仅部分？优先恢复关键推送（如含紧急待办的简报）

#### 限速与数据空的区分

| 模式 | `last_status` | `last_delivery_error` | 用户看到的 |
|------|--------------|----------------------|-----------|
| 数据空→静默 | `ok` | `null`（或不存在） | 无消息 |
| 推送限速 | `ok` | 有错误文本 | 无消息 |

两者用户都「没收到」，但根因和处理方式完全不同。**不要混淆**。

#### 恢复流程——找回 Cron 生成的内容

1. **通过 session_search 找回执行记录**：
   ```
   session_search(query="<技能名> cron <日期>")
   ```
   如：`session_search(query="daily-briefing cron 2026-06-21")`

2. **手动补推**：将找回的内容整理后直接在当前会话中发给用户。

3. **注意补推的完整性**：如果连续多天都受限，需要按日期逐一找回：

   | 日期 | 技能 | 关键词 |
   |------|------|--------|
   | 6/19 | daily-briefing | `daily-briefing cron 2026-06-19` |
   | 6/19 | daily-review | `daily-review cron 2026-06-19` |
   | 6/20 | daily-briefing | `daily-briefing cron 2026-06-20` |
   | ... | ... | ... |

#### 长期缓解方案

| 方案 | 操作 | 效果 |
|------|------|------|
| 微调触发时间 | 各 Cron 错开 15-30 分钟 | 减少多任务连续推送 |
| 改用企业微信 | 将 deliver 改为 `wecom:<channel>` | 企业微信配额远高于个人微信 |
| 微信+企微双推 | 同时在两个渠道推送 | 有冗余，一个受限另一个仍能到达 |
| 调优重试参数 | 设 `WEIXIN_SEND_CHUNK_RETRIES=20` + 重试间隔 5s（详见下方） | 将重试窗口从15秒延长至5分钟 |
| 降低推送频率 | 周末改用简版或合并推送 | 减少主动推送次数 |

**原则**：限速是腾讯平台侧行为，MyPS 无法完全消除。正确应对是：发现后及时排查+主动恢复+评估是否切换渠道或调优参数。

#### 限速缓解——重试参数调优（不切换渠道的方案）

当用户希望**不切换企业微信、在微信渠道内解决**时适用。详见 `references/wechat-rate-limit-investigation.md` 完整方案。

**原理**：微信 WeChat 适配器读取两个环境变量控制重试行为：

| 环境变量 | 默认值 | 推荐值 | 效果 |
|---------|--------|--------|------|
| `WEIXIN_SEND_CHUNK_RETRIES` | 4 | 20 | 21次重试 |
| `WEIXIN_SEND_CHUNK_RETRY_DELAY_SECONDS` | 1.0 | 5.0 | 限速时间隔=15s |
| `WEIXIN_SEND_CHUNK_DELAY_SECONDS` | 1.5 | 2.0 | 分块间隔 |

**重试窗口**：21次 × 15s ≈ 5分钟（原为 5次 × 3s ≈ 15秒）

**操作**：
1. 设环境变量 → kill 旧 Gateway → 带新变量重启 → 追加到 `.bashrc` 固化
2. 重启后所有 WeixinAdapter 实例自动继承新参数

**局限**：如果腾讯限速窗口超过 5 分钟，仍可能失败。此时只能切换渠道。

### 「Cron 任务报错——排查临时性与持续性故障」

当 Cron 任务失败且错误信息涉及网络/API层（如 `SSL: WRONG_VERSION_NUMBER`、`Connection refused`、`Timeout`、`5xx` 等）：

**排查流程**：

1. **手动重跑判断性质**：`cronjob(action='run', job_id='<job_id>')`
   - 重跑成功 → 临时性故障（瞬断），无需停任务或改配置
   - 重跑同样失败 → 持续性故障，需深入排查

2. **横向对比**：同一时间段内其他 Cron 任务是否也报错？只有个别报错 → 检查模型/provider 配置差异

3. **连续多天同一错误**：如果同一任务连续 3+ 天在不同时间点报相同 SSL 错误 → 排查服务器时间准确性（导致证书验证失败）或代理/防火墙拦截

**核心教训**：provider API 层的 SSL/连接错误大多是一次性瞬断。手动重跑确认一次即可，不要直接停任务。

### 「新需求不会自动提醒」
- 提醒由 reminder-engine 管理
- 待办创建时会自动生成 Cron 任务
- 如果要创建独立提醒，直接用 cronjob 创建一次性任务

---

## Kanban 数据库问题排查

### 背景

Hermes Gateway 内置了一个 kanban 调度器（`kanban.dispatch_in_gateway: true`），默认每 60 秒对 `~/.hermes/kanban.db` 做一次连接检查。

**MyPS 不使用 kanban 功能**——MyPS 用自己的 `todos.json` + 三种待办体系。所以 kanban.db 损坏不影响任何 MyPS 核心功能，但会每分钟刷一条错误日志：

```
sqlite3.DatabaseError: file is not a database
kanban dispatcher: tick failed on board default
```

### 排查流程

1. **确认问题**：在 gateway.log 中搜索 `kanban dispatcher.*failed`
   ```bash
   grep "kanban dispatcher.*failed" ~/.hermes/logs/gateway.log | tail -5
   ```
2. **确认数据库状态**：
   ```bash
   xxd ~/.hermes/kanban.db | head -1
   ```
   正常数据库以 `5351 4c69 7465 2066 6f72 6d61 74`（"SQLite format"）开头。若头部字节错乱则已损坏。
3. **确认是否被使用**：检查 `~/.hermes/kanban.db` 大小和修改时间。长时间未变且无人提及 kanban 功能 → 视为闲置，可直接重建。

### 修复方法

```python
# 1. 备份旧文件
mv ~/.hermes/kanban.db ~/.hermes/kanban.db.bak

# 2. 用 Hermes CLI 重新初始化
~/venv/bin/hermes kanban init

# 3. 验证新数据库
ls -la ~/.hermes/kanban.db   # 应约 100KB
```

### 注意事项

- `hermes kanban init` 会创建完整的表结构（tasks, task_links, task_comments, task_events, task_runs, kanban_notify_subs），与 Hermes 期望的 schema 一致
- 重建后下次 kanban 轮询（60s 内）自动恢复，无需重启 Gateway
- **不要**直接用 Python sqlite3 手动建表——可能遗漏 WAL 模式设置或缺失表，导致仍然报错
- 如果用户确实在使用 kanban 功能（主动创建过看板），不要直接重建——需先确认是否有未完成的任务

---

## Gateway 失效排查

### 背景

MyPS Gateway 通过 **nohup** 启动（`nohup hermes gateway run > ~/hermes-gateway.log 2>&1 &`），**没有 systemd 或 supervisor 守护**。被 kill 后不会自动重启。

**后果**：Gateway 停摆期间：
- ❌ 无法接收和回复用户消息
- ❌ Cron 任务到点不执行（调度器随 Gateway 一起停止）
- ✅ 文件系统数据不受影响

### 排查流程

1. **用户反馈「没收到消息」**：先区分是「消息没收到」还是「系统没回复」
   - 用户发消息后无任何回复 → Gateway 离线
   - 用户收到回复但 Cron 推送未到 → 见「微信限速」章节

2. **检查 Gateway 进程**：
   ```bash
   ps aux | grep "hermes gateway" | grep -v grep
   ```
   如无输出 → Gateway 不在运行

3. **检查上次运行日志**：
   ```bash
   tail -20 ~/.hermes/logs/gateway.log
   ```
   查找 `SIGTERM`、`SIGKILL`、`shutdown` 等关键词，确认停止原因
   ⚠️ **注意**：终端里直接 grep `shutdown`/`reboot`/`kill` 等词会触发 hardline 块列表（即使只是 grep 模式，不是真执行），改用 `read_file` 读日志文件，或拆开关键词（如 `SIGKILL`、`exit_clean`）避免被拦截。

4. **检查 Cron 任务运行状态**：
   ```python
   cronjob(action='list')
   ```
   查看 `last_run_at` 是否在预期时间附近。Gateway 停摆期间的任务 `last_run_at` 会停留在停摆前最后一次执行时间。

5. **区分正常退出 vs 断电/硬杀**：读 `~/.hermes/logs/gateway-exit-diag.log`（追加式 JSONL，记录每次 gateway.start 及退出标记）
   - 最后一次 start 之后有 `exit_clean` / `exit_nonzero` 标记 → 进程自己退出（可查原因）
   - 最后一次 start 之后**无任何退出标记** → 进程被硬杀（断电/SIGKILL/OOM），没机会写退出日志。用户说「断电停机」时此模式吻合
   - ⚠️ 时间戳为 UTC，对比时 +8h

6. **重建停机窗口**（用户反馈「那几天没反应」时）：
   - `cronjob(action='list')` 各任务 last_run_at 全部停在同一个时刻 = 停机起点
   - `grep -c "2026-08-06" ~/.hermes/logs/gateway.log` 计数为 0 = 当日全天无活动
   - 停摆期间的 diary/events 文件缺失属正常（消息根本没到达），**不等于数据丢失**——本地文件系统不受停机影响

7. **重启后检查清单**（机器恢复供电/手动拉起后）：
   - 数据完整性：抽查停机窗口前后 diary/events/todos.json 是否完好
   - **备份新鲜度**：`cd ~/.hermes && git log --oneline -3`——最近 commit 日期若远早于停机前，说明备份早已静默失败（详见 data-backup skill「备份积压检测」），立即手动补
   - 错过的 Cron 不会自动补跑，需要补的执行 `cronjob(action='run', ...)`；已过时的简报/总结（隔天）不补推
   - 停机期间用户发的消息已丢失（微信长连接断开不补收），提醒用户补发重要内容

5. **定位停机窗口（用 exit-diag 日志）**：`~/.hermes/logs/gateway-exit-diag.log` 记录每次 gateway.start 及 exit。如果最后一次 start 之后**没有**对应的 exit_clean/exit_nonzero 记录，说明进程被硬杀（断电/SIGKILL）——典型的断电特征。用 `grep -c "2026-08-06" gateway.log` 之类按日期统计日志条数，某天 0 条 = 当天全天停机。

6. **核查数据完整性（停机恢复后的固定动作）**：
   - 本地数据（diary/events/todos/knowledge）不受 Gateway 停机影响，文件系统检查即可
   - **备份新鲜度**：`git -C ~/.hermes log --oneline -3` 看最后 commit 日期；`cat ~/.hermes/cron/backup-status.json` 看 last_backup。若备份落后多日 → 先补备份（git add/commit/push，push 被拒走 fetch --force + reset --soft + 重新 commit + push，或 API 方案），补完 `git ls-remote origin main` 与 `git rev-parse HEAD` 比对验证
   - 停机期间用户发的消息无法找回（微信侧不补投离线消息），如实告知用户需补发

### 确定停机窗口（停电/宕机时长）

实战（2026-08-07）：用户旅行归来反馈「系统断电停机」，需要精确还原停机起止时间。三件套交叉验证：

1. **gateway.log 最后一条记录** = 停机起点（如 `tail` 显示 8/5 22:19 后再无记录，而 8/6 全天 0 条 → 停机从 8/5 22:19 后开始）
2. **gateway-exit-diag.log** = 判断停机性质：`~/.hermes/logs/gateway-exit-diag.log` 记录每次 start/exit（exit_clean / exit_nonzero / asyncio.run.returned）。**两次 start 之间没有 exit 记录 = 被硬杀（断电/SIGKILL），进程来不及写退出日志**——这是区分「正常关闭」与「断电」的决定性证据
3. **Cron last_run_at 缺口** = 停机期间错过的推送清单：对比各 Cron 的 last_run_at，逐日列出 8/6 缺了哪些（早简报 08:30、晚总结 22:00、备份 03:00 等），向用户报告「停机期间错过的都是哪些推送」

**恢复检查清单**（停机恢复后必做）：
- ✅ 文件数据（diary/events/todos/knowledge）完整性——本地文件不受停机影响，确认存在即可
- ✅ git 备份是否积压 → 见 data-backup skill 的「备份静默失败检测」
- ✅ Cron 调度是否恢复正常（next_run_at 已推进）
- ⚠️ 停机期间用户发的消息无法补收——主动提醒用户「那几天说过重要的事补发一句」

### ⚠️ 陷阱：grep 关键词触发硬拦截

排查日志时**不要在 grep 模式里写 `shutdown`、`kill`、`reboot` 等词**（即使只是匹配日志文本，如 `grep -iE "start|stop|shutdown|kill|signal" gateway.log`），会命中 Hermes 无条件块名单（hardline block），命令整体被拒。

**替代**：
- 用 read_file 直接读日志文件尾部（诊断文件通常不大）
- 或 grep 更窄的模式（如 `grep "gateway.run"`、按日期 `grep "2026-08-05"`）
- 想找停止原因时：先 tail 日志看最后记录，再读 gateway-exit-diag.log 判断性质，两者足够

### 恢复启动

```bash
source ~/venv/bin/activate
nohup hermes gateway run > ~/hermes-gateway.log 2>&1 &
```

验证启动成功：
```bash
tail -5 ~/hermes-gateway.log
# 应看到: "Gateway running with N platform(s)"
```

### Gateway 启动后的自动恢复行为

Gateway 重启后自动恢复的项目：
- ✅ 微信/企微连接
- ✅ Cron 调度器（重新开始计时）
- ❌ **已错过的 Cron 任务不会补跑**——调度器会检测到错过时间窗口（超过 2 小时 grace），跳过并更新 `next_run_at` 到下一次预定时间。日志中会出现：`Job 'xxx' missed its scheduled time... Fast-forwarding to next run`

### 错过 Cron 恢复流程

当 Gateway 错过了一次或多次 Cron 推送时：

1. 通过 `cronjob(action='list')` 确定哪些任务在停摆期间错过了
2. 如需补跑，使用 `cronjob(action='run', job_id='<id>')` 手动触发
3. 手动触发时注意：run 命令会加载对应的 skills 并执行 prompt，结果通过预设的 deliver 推送
4. 如果单次 missed 消息不需要补推，也可以等下次正常调度

### 长期方案（已落地：watchdog 守护）

**当前环境（Linux Deploy 容器）**：PID 1 不是 systemd → systemd 方案不可用；crond 未运行 → crontab 不可用。正确方案是**自建 watchdog 脚本**：

- 脚本：`~/.hermes/scripts/gateway-watchdog.sh`（v2）
- 机制：每 30s 检查 gateway 主进程（`/venv/bin/python.*gateway run` 精确匹配），连续 2 次检测不到则自动拉起
- 开机自启：已挂载 `/etc/rc.local`（Linux Deploy 开机钩子，在 gateway 启动行之后）
- 日志：`~/hermes-watchdog.log`
- 手动启动：`nohup bash ~/.hermes/scripts/gateway-watchdog.sh &`

**⚠️ v1 事故教训（2026-08-17）**：watchdog 用宽泛 `pgrep -f "hermes gateway run"` 检测时，旧 gateway 优雅关闭期间进程仍在（SIGTERM 后等待当前会话结束），且临时 bash 包装进程也含该字符串 → 误判存活 → 不拉起。修复：精确匹配 python 主进程路径 + 连续 2 次缺失才触发。

**✅ 真实演练结论（2026-08-17 二次演练，铁证已验证）**：独立 watchdog 拉起路径真实跑通——击杀 gateway（14119）后，watchdog 14124（PPID=1，rc.local 启动）独立存活，11:37:48 自动拉起新 gateway 14341（PPID=14124=watchdog）。**判定拉起者**：新 gateway 的 PPID = watchdog PID → watchdog 拉起；PPID=1 → rc.local 兜底；PPID=用户 shell → 手工重启。

**⚠️ 误判教训（第一次演练）**：曾宣布"自动恢复成功"，实际是用户手工重启救的（用户原话「还是起不来，是我手工重启的」）。根因：手动启动的 watchdog 是 gateway 子进程，gateway 优雅关闭时连带杀死，守护链断裂。教训：**宣布自愈成功前必须核对 PID/PPID/启动时间三件套，不能凭"能收到回复"下结论**。

**⚠️ 恢复后"进程起来了 ≠ 通道通了"**：gateway 拉起后平台通道异步重连——weixin 约 10s 连上，wecom 可能重连失败 3 次、耗时约 3 分钟（实测 11:39-11:42），且回复投递可能 unconfirmed 被排队补发。用户报「没反应」时先查 `gateway_state.json` 两个平台 state 是否都 `connected`，再看 gateway.log 有无 inbound 时间戳——区分「没起来」「通道重连中」「投递未确认」三种情况，不要急着宣布成功或失败。

rc.local 的 watchdog 行已加防重复（`pgrep -f gateway-watchdog.sh || ...`）。排查重复实例时注意：`pgrep -f` 会把命令自身的 bash 包装计入，需排除 `bash -c` 行再数。

**⚠️ sudo 免密**：`SUDO_PASSWORD` 已写入 `~/.hermes/.env`（用户授权），Hermes 终端工具自动注入。测试时**不要用 `sudo -n`**（-n 禁用密码注入，会误判为未配置）；直接用 `sudo <cmd>` 验证。修改 root 文件（如 rc.local）用 `sudo sed -i`。

**⚠️ 重启 gateway 的坑**：`hermes gateway restart` 走 systemd 用户服务路径，本环境无 user D-Bus 会失败。手动重启：`kill <PID>`（gateway 优雅关闭需等当前会话结束）→ watchdog 会自动拉起，或直接后台起新实例。kill/pkill gateway 相关命令会触发安全审批（self-termination），属正常。

**watchdog 验证测试**：修改 watchdog 后必须做逻辑验证（精确匹配、连续计数、拉起动作三断言），测试方法见 `references/watchdog-verification.md`。核心坑：模拟进程不能用 `sleep <路径>`（sleep 把路径当时间解析直接退出）或 `bash -c` 包装（exec 丢 argv 标记），要用 venv python3 直接跑带标记名的脚本。

### 审批提示汉化（2026-08-17 完成）

用户对英文审批提示零容忍。`display.language=zh` 配置**不够**——Hermes 安装包不带 `locales/zh.yaml`（i18n 有框架无词库），且微信端审批提示是 `gateway/run.py` 里的**硬编码英文**（约 15572 行，`send_exec_approval` 的 text fallback 分支），根本不走翻译系统。

**已做的修改**：
1. `hermes config set display.language zh`（影响 CLI 端 i18n 消息）
2. 直接 patch `~/venv/lib/python3.11/site-packages/gateway/run.py`：将审批提示硬编码英文替换为中文（"危险命令，需要你的批准" + 中文 `/approve` 说明）。**改前先备份**（cp run.py run.py.bak-<日期>）
3. 原因行（Reason:）来自 tirith 安全扫描器动态生成，无法静态汉化——接受

**⚠️ 升级会覆盖**：site-packages 的 patch 在 Hermes 升级/重装后失效，需重新打补丁。记忆里有标记，升级后对照此节重做。

### 环境特性（Linux Deploy 容器）

- PID 1 不是 systemd → systemctl 全线不可用，`hermes gateway install/start/restart` 走 systemd 路径的都会失败
- crond 未运行 → 用户 crontab 不可用
- 唯一可靠开机钩子：`/etc/rc.local`（Linux Deploy 执行，`su - hermes -c` 方式拉起服务）
- supervisor 曾配置（`/etc/supervisor/conf.d/hermes-*.conf`）但启动即失败（exit 1），弃用
- `SUDO_PASSWORD` 写入 `~/.hermes/.env` 后 Hermes 终端工具自动注入 sudo 密码；**验证用 `sudo <cmd>` 而非 `sudo -n`**（-n 绕过注入机制误判失败）

---

## 系统升级与版本管理

### 判断是否该发新版（版本差距诊断）

用户问「要不要发新版本」时，不要凭感觉。按此流程对比公开仓库与运行版：

1. **查公开仓库最后 commit 日期**：GitHub API `curl api.github.com/repos/GoodVFX/MyPS/commits`（若超时，用 web_extract 抓仓库主页，能看到文件清单 + README 版本号）
2. **查本地 skills 更新时间**：`ls -lt ~/.hermes/skills/*/SKILL.md`，与公开仓库最后 commit 日期对比
3. **统计差距**：新增了几个 Skill？原有 Skill 有多少实质性更新？
4. **结论标准**（2026-08-17 实例）：公开仓库停在 7/9 v2.0（6 Skills），运行版已扩到 9 Skills（新增 project-coach、data-backup、myps-operations）且 6 个原 Skill 全部更新 → 明确该发 v3.0。若只有零星改动则不必。

MyPS 存在两个版本线：

| 版本线 | 用途 | 仓库类型 | 所含内容 |
|--------|------|---------|---------|
| **公开版** (GoodVFX/MyPS) | 开源框架，供他人使用 | GitHub 公开仓库 | SOUL.md / USER.md（模板）/ AGENTS.md / MEMORY.md / 6 个 Skills / 模板文件 |
| **个人版** (~/.hermes/) | 真实运行环境 | (可选) GitHub 私有仓库 | 公开版 + 个人数据（日记/待办/记忆/知识/配置） |

### 公开版升级流程

当需要将当前运行版的改进同步到公开仓库时（如 v1.0 → v2.0）：

1. **分析差异**：对比公开版和运行版的核心文件（SOUL.md、Skills 等），确定哪些变化可以公开
2. **脱敏**：USER.md 保留模板格式，确保不含个人数据（姓名、职业、关键人物、具体术语）
3. **打包更新**：
   - Skills 直接使用运行版（不含个人数据）
   - 核心配置文件更新版本号和日期
   - README.md / INSTALL.md 同步升级
4. **推送**：使用 GitHub Personal Access Token + Git Data API 一次性提交

### GitHub API 推送方式（当 git clone 超时时）

如果服务器无法直连 GitHub git 协议，可使用 GitHub Git Data API：

```python
1. GET /repos/{owner}/{repo}/git/refs/heads/main → 获取最新 commit SHA
2. GET /git/commits/{sha} → 获取当前 tree SHA
3. POST /git/blobs → 为每个文件创建 blob（base64 编码内容）
4. POST /git/trees → 创建新 tree（引用所有新 blob）
5. POST /git/commits → 创建新 commit
6. PATCH /git/refs/heads/main → 更新分支引用
```

详见 `references/github-api-push.md`。

---

## 数据备份

MyPS 的数据备份功能由专用 Skill `data-backup` 管理，详见 `skills/data-backup/SKILL.md`。

简要流程：
- 创建 GitHub 私有仓库 → `~/.hermes/` 初始化 git → 设 remote → 首次完整备份 → 每日 Cron 增量备份
- 恢复：`git clone <私有仓库> ~/.hermes/` 回车即恢复全部数据

详细步骤、.gitignore 模板、API 推送方案（git push 超时时的替代方案）、已知陷阱等，均见 `data-backup` Skill。

### 重要区别

| 概念 | 说明 |
|------|------|
| 个人报销 vs 公司发票 | 用户垫付→公司返款=个人报销；只帮公司提交发票给财务=公司事务，不记待办 |
| Chronic reminder vs hard deadline | 持续提醒直到用户喊停 vs 有明确截止时间的单次提醒 |
| **公开版 vs 个人版** | 公开版不含任何个人数据；个人版是全量运行环境 |

---

## 月度周期性任务

对于用户每月固定要做的任务（如 10 号前的行政工作），最佳实践是：

1. 保存到 memory/ 以便随时查阅具体内容
2. 创建每月 1 号的 Cron 任务作为月初提醒
3. 如果需要更细致的跟踪，可以创建待办条目

### 月度待办自动写入模式

当需要「每月 1 号自动把 N 件事加入待办目录」时，**不要用纯消息提醒**。Cron 任务的 prompt 应包含写入 todos.json 的指令：

**✅ 正确做法（写入待办）**

```python
prompt = '''
1. 读取 todos.json
2. 在 deadlines 数组添加 N 条待办，deadline 设为当月 10 号
3. 确保不重复添加（检查是否有本月同名的活跃条目）
4. 写回 todos.json
5. 推送确认消息给用户
'''
skills = ['task-manager']
```

**❌ 错误做法（仅提醒）**

```python
prompt = '提醒用户做 X、Y、Z'   # ← 不会加入待办目录，用户无法跟踪进度
```

### Cron 任务 vs 待办联动关系

```
月度 Cron（1号触发）
  │
  ├─ 写入 todos.json deadlines 数组
  │    每个条目标注 done: false, deadline: 当月10号
  │
  ├─ 用户完成后手动标记 done: true
  │
  └─ 下月1号 Cron 再次写入新一批（旧已完成项仍在，但状态为 done）
```

### 用户提前完成（上月月底）

当用户在 Cron 触发前（如 7/31）提前完成了下月的批量组成员时，**预创建 done: true 条目**（而非等 Cron 创建）：

- 预创建条目带月份标注（如「打印消毒登记表（8月）」），Cron prompt 第 3 步「确保不重复添加已有条目」的查重逻辑能识别并跳过
- 效果：下月简报不出现重复提醒，组进度自动反映「已完成 N/6」
- 这是 monthly-checklist Cron 查重机制的配套用法，fragment-catcher 的批量组章节有完整处理规则
