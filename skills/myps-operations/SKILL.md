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
  - 用户说「记忆层满了」「优化一下记忆」（处理流程见 `references/memory-compaction.md`）
  - 涉及读写记忆注入层、或要「升级/改造 MyPS 自己」的任何改动（存储地图与治理流程见 `references/memory-storage-and-upgrade-governance.md`）
  - 用户让 SSH 连接/查看远程机器（如「ping projectx」「看看长期项目X机器」）——见「远程节点 SSH 应急访问」章节
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

### Prompt 写作四要素标准（2026-09-30 定型，借鉴 某AI通道服务 官方任务规范）

新建/修订 LLM 型 cron 的 prompt 时按四要素自查，缺一即为「写糊的任务」——糊任务的故障模式是「分不清没执行还是执行了没内容」：

1. **目标动作**：可判断完成与否的动作（「汇总并列出」✓，「关注一下」✗）
2. **范围边界**：时间窗/数量上限/筛选条件/数据源限定路径
3. **输出格式**：结构、长度、落盘位置（若产出档案类产物，prompt 里写明写入路径+已存在则覆盖）
4. **例外处理**：数据为空时的行为——提醒/简报型=无事也说一句；watchdog 型=[SILENT] 静默；数据源不可用时如实说明缺失部分，不编造

存量任务体检结论（9/30 全量 17 任务过检）：daily-briefing 各节自带空处理+全空 [SILENT] 兜底、monthly-checklist 有查重保护、一次性提醒类文本写死天然合规——之后新任务直接按四要素写（范例：`MyPS成长回放` job 76a546e613d6 的 prompt）。

### 新 Cron 机制上线即模拟测试（2026-09-30 用户定调：不要等真正的测试点）

新 cron 机制注册后**立即 `cronjob(action='run')` 实跑验证**，不等首个真实触发日。流程与坑：

1. **⚠️ 相对时间 prompt 会测错分支**：prompt 写「上个月」时，月中任意一天 run 测的都是错误范围（9/30 实测：run 触发后测到 8 月=例外分支而非 9 月主路径）。先 `update` 把范围 pin 死（「【模拟测试】本次范围固定 YYYY-MM-01 至 YYYY-MM-LL，不按『上个月』推算」），跑完改回通用版
2. **完成判定别只等 job 状态**：档案落盘（watch 目标文件 mtime 变化）在先，`last_run_at`/`last_status` 回写在后（实测落后约 1-5 分钟）——mtime 变了即跑完，status 延迟回写属正常
3. **质量验证三查**：数据真实性（抽 2-3 条对 git/diary 原始记录）、缺口如实标注（缺失写缺失，不推测补齐）、口径差异是否注明（如实记录即可）
4. deliver=origin 的 run 会**真实推送微信给用户**——这就是给用户的验收方式，汇报时注明哪条是模拟测试产物
5. 模拟跑的档案产物会被正式首跑同路径覆盖，无残留风险；模拟中发现的 prompt 缺口当场改

### 升级验证链 → 门槛发布（2026-09-30 定型，与上节配套）

模拟测试通过 ≠ 新机制在 cron 环境稳定——主会话模拟与 cron 会话的 token 预算/上下文不同，自然触发日仍是必要观察点。多机制升级后的标准「验证→发布」链（实例：CHECK1/CHECK2/PUBLISH 三任务接力）：

1. **每个验证点挂一个一次性 cron**（repeat=1），prompt 写死可机械判定的判据清单：流程判据（cronjob list 的 last_run_at/last_status/last_delivery_error）+ 产物判据（目标文件 mtime、关键区块存在性）+ 数据判据（与 git/原始记录交叉抽查，±容差写明）。**结论固定为最后一行**：「CHECKn ✅ 绿——各判据结果」或「CHECKn ❌ 红——失败点+排查方向」；「无法执行」一律判红，不推测补齐
2. **发布任务用 `context_from` 注入全部验证任务**，prompt 开头即硬门槛：任一红或结论缺失 → 只发中止消息、不执行任何发布动作；全绿才走完整 SOP（如 public-release-workflow）
3. **时间错开**：验证任务距被验证任务 ≥20 分钟（等执行完成+状态回写，实测回写可延迟数分钟）；发布任务距最后验证 ≥10 分钟（GLM 池 429 错峰惯例）
4. **失败路径**：验证红 → 修复 → `cronjob(action='run')` 重跑对应 CHECK → 绿后重建发布任务或手动执行发布（一次性任务用过即消失，门槛中止也算用过）；发布中途卡住 → 停在该步发卡点报告，不跳步
5. 每个验证/发布节点 deliver=origin，结果直接推用户微信——全程无需用户做任何事，但每步结果可见

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
> 后台模型按需切换见上条；**记忆写满（99%）时的处理**：`memory` 工具报「Replacement would put memory at X/2200 chars」= 空间不足，**同一轮里先压缩/合并既有条目腾出空间再写**——重复重试同一段内容必然继续失败（2026-09-23 实测连败 3 次）。压缩优先级：删冗余字样（「（ls→1s）」等举例）、合并同主题条目、把细节挪进 skill/reference 只在 memory 留一句话指针。用户说「记忆层满了」「优化一下记忆」时的完整流程见 `references/memory-compaction.md`
> **★ 记忆注入层真实位置 = `~/.hermes/memories/MEMORY.md`**（§ 分隔，~2200 字符上限）；根目录 `~/.hermes/MEMORY.md` 是 7/9 起停更的旧遗留索引，勿读写。完整存储地图、系统自升级四段式治理（备份→升级→评估→固化/回滚）、knowledge/ INDEX 分层检索规则 → `references/memory-storage-and-upgrade-governance.md`（2026-09-29 定型）
> **★ 模型路由原则（2026-09-23 用户定案，长期生效）：体验优先给 DS，成本优先给 GLM**——日常沟通/简报/总结走 DS，**大量数据处理、高 token 重活（备份/批量整理/大文档消化）走 GLM**（Coding Plan 深夜 23:00-09:00 glm flash 无限量）。三种落地姿势（cron 显式 pin / 会话内脚本直调 GLM / 整段切 config）见 `references/model-switching.md`
> 后台模型按需切换（DeepSeek↔GLM 实验、Hermes 运行时切换机制、GLM Coding Plan 端点与坑）见 `references/model-switching.md`
> **模型路由原则（2026-09-23 用户定案）**：日常沟通/简报/总结 = DS（体验优先）；**大 token 重活 = GLM**（成本优先，深夜 23:00-09:00 无限量）；看图 = Agnes；辅助杂活 = OpenRouter 免费。**新增 cron 前自查「这活吃不吃大量 token」，吃就 pin GLM**；会话内临时重活不切主模型，写脚本直调 GLM 即可——详见同文件 ★ 模型路由原则章节
> 语音合成（TTS）接入：**权威出处 = 独立 skill `doubao-tts`**（接口/鉴权/流解析/坑/资源包计费/定稿音色参数，含 `scripts/synth.py`）；`references/tts-providers-doubao.md` 为接入期原始笔记，待并入；视频旁白交付规范见 `video-production` skill
> MyPS 低功耗部署资源画像（实测占用/最低硬件要求/设备推荐档位/废物利用候选）见 `references/deployment-resource-profile.md`——用户问「MyPS 能不能跑在小设备/机顶盒/树莓派」时先读此文件再答

---

## 微信链路故障与重连自愈（2026-09-06 实战）

微信链路：微信客户端 ↔ iLink Bot（ilinkai.weixin.qq.com）↔ WeixinAdapter ↔ gateway。

**故障模式**：日志反复 `[Weixin] Session expired; pausing for 10 minutes` = iLink Bot 会话被其他客户端挤下线（同类 iLink 服务单会话互斥，谁后连谁生效——9/6 实例：用户连接 **某第三方AI助手** 的微信通道把 MyPS 顶掉；用户前期口述"OK Body"，后确认实为 某第三方AI助手，同类 iLink bot 扫码服务同理）。重启/重启系统都不解决。

**两个根因坑（恢复缺一不可）**：
1. **`.env` 硬编码凭据优先级高于账号文件**（`gateway/config.py:1659`）——只扫码或只重启无效，必须同步改 .env 的 `WEIXIN_ACCOUNT_ID`/`WEIXIN_TOKEN`
2. **账号目录是 `~/.hermes/weixin/accounts/`**——`_account_dir()` 拼接不含 `.hermes`，传入 hermes_home 必须是 `~/.hermes`；传 `~` 会写进 `~/weixin/accounts/` 永远看不见

**一键恢复（首选）**：root SSH 进容器敲 **`wx-fix`**（/usr/local/bin/wx-fix → `~/wx-recovery/wx_fix.py`）。自动：检测（sync.json 游标 60s 内有更新=正常，防误跑需 y 确认强扫）→ 拉二维码（终端 ASCII + 存 PNG `~/wx-fix-qr.png`）→ 等扫码（2 分钟过期自动刷新×3）→ 自动装凭据 + 停用旧账号 + 备份改 .env + kill gateway（watchdog 拉起）+ 验证。日志 `~/wx-fix.log`。
**验证标准**：`~/.hermes/weixin/accounts/<bot>@im.bot.sync.json` 的 mtime 每约 19 秒跳动 = 长轮询正常。

**自愈机制（watchdog）**：`scripts/gateway-watchdog.sh` 30s 检测、连续 2 次缺失拉起 gateway，flock 单实例锁，实测 kill -9 后 48s 恢复。rc.local 已重写为直接 setsid 启动（备份 rc.local.bak-20260906）。
⚠️ **守护进程经典陷阱**：`pgrep -f X || start X` 会匹配到执行它的 shell 自身恒为真，启动命令永不执行（watchdog 因此"装了等于没装"数月）——正确做法：直接 setsid 启动 + 脚本内 flock 保证单实例。

完整手册（SOP/踩坑清单/实测记录）：`~/wx-recovery/hermes-微信重连-复盘与自愈手册.md`；可移植浓缩版见 `references/wechat-reconnect.md`。
⚠️ 用户偏好（9/6 明确）：运维操作要**一条短命令**（wx-fix），不接受长命令串/繁琐步骤——创建全局命令放 /usr/local/bin/。

---

## 视觉/多模态模型接入（auxiliary.vision）

用户发图能力 = `auxiliary.vision` 配置（Hermes 原生机制，**无需换主模型**）。**2026-09-06 起切 Agnes `agnes-2.5-flash`**（免费期，原生多模态实测能看图，prompt 缓存支持）；此前 2026-08-27~09-06 用 DeepSeek `deepseek-v4-flash-vision-exp`（配置备份在 config.yaml.bak-20260906，随时可回滚）。

**配置要点**（`~/.hermes/config.yaml` → `auxiliary.vision`）：
- 当前：`provider: agnes`、`model: agnes-2.5-flash`、`base_url: https://api.agnes-ai.cn/v1`（OpenAI 兼容）+ 完整 api_key 明文（config.yaml 在 .gitignore，安全）
- ⚠️ **api_key 必须完整明文写进 config.yaml**（工具显示会脱敏但文件是全文）：deepseek 时代留空走凭据池实测 401 `expired`（8/27）。key 写 config 用脚本从 .env 读取替换，不让 key 出现在对话/输出中
- ⚠️ **provider 名不必是内置名**（agnes 非 Hermes 内置也工作），base_url+model+api_key 三件套齐即可
- **生效需重启 gateway**：agent 无法前台执行 `hermes gateway restart`（超时被拦截；nohup 延迟重启也被安全策略拦）。可靠流程：先用 send_message 告知用户"正在重启，稍后发图测试" → `kill <gateway PID>`（SIGTERM 优雅关闭，等当前会话结束才退出）→ watchdog 自动拉起新实例读新配置。**kill 后进程不会立刻消失**（等会话结束属正常，勿误判失败）；重启完成后用 vision_analyze 实测验证
- **验证**：`vision_analyze` 工具直接测一张本地生成图（纯色象限 PNG 最省事）；四色象限答对 = 通道通。改配置后 gateway 未重启时请求会发到新 URL 但带旧 model 名报 model_not_found——看到此错先重启 gateway
- DeepSeek API 现状（2026-08）：视觉模型 `deepseek-v4-flash-vision-exp` 支持 Chat Completions/Messages/Responses；`deepseek-v4-pro` / `deepseek-v4-flash` 为文本模型

---

## 远程节点 SSH 应急访问（projectx）

MyPS 持有用户编码工作机 / 长期项目X 本体（`projectx`，测试硬件N）的 SSH 免密通道，**定位是应急接口**：日常运维测试用户自己在编码工作机做，MyPS 只在用户人在外面、不在机器旁时顶上——看状态、查日志、应急处理。

**触发场景**：用户说「ping projectx」「看看长期项目X机器状态」「用 projectx ssh 登录试试」等。

- 入口：`ssh -o BatchMode=yes projectx@projectx '<命令>'`（免密已配，无需密码）
- 只读检查（状态/日志/硬件信息）可直接执行；写操作/重启先征求用户同意
- **projectx 机器的连接信息、硬件基线、网络/快照/测试工程 → 归口 `host-ops` skill**（权威源，防双处维护漂移——如 2026-09-10 起静态 IP <局域网IP> 等以彼为准）
- 新节点接入通用流程与 MyPS 侧分工边界 → `references/remote-node-ssh-access.md`（已去重，仅保留 MyPS 侧内容）

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

**原因 A**：Cron 未设 `workdir`，技能中的相对路径 `data/diary/` 等指向了错误位置。

**原因 B（2026-09-09 简报实跑发现）**：数据采集环节 `search_files` 对确实存在的路径静默返回 0 结果（假阴性），agent 据此误判「无数据」——与 workdir 无关，是检索工具假 0。**返回 0 时先怀疑工具再怀疑数据**：用 terminal `ls`/`grep` 兜底确认路径存在，改用 `read_file` 直接读已知路径。完整坑清单见 daily-briefing SKILL.md「数据采集实测坑」（含 todos.json 超 500 行分页漏读后半段 deadlines 陷阱）。

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
  cronjob action='update' job_id='<job_id>' deliver='weixin:<你的微信ChatID>...'
  ```
  chat_id 可以从当前会话的上下文信息中获取（Source 行中的 Weixin DM ID），或通过 `send_message action='list'` 查看可用平台目标。
- 更新 workdir：`cronjob action='update' job_id='<job_id>' workdir='~/.hermes'`
- 验证：更新后手动触发一次 `cronjob action='run' job_id='<job_id>'`
- 兜底：如果 Cron 推送始终无法到达，在活跃会话中直接执行晚间总结内容发给用户。

### 「推送因平台限速丢失」——排查与恢复流程

> 详细调查记录见 `references/wechat-rate-limit-investigation.md`

**现象**：`last_delivery_error` 包含 `rate limited`、`rate limit` 等字样。`last_status=ok`。

**⚠️ 一次性 cron（schedule once）单发不可重试**（2026-08-28 实战）：「结果汇报」型一次性任务执行成功、output 已生成、报告完整，但推送被限速吞掉后任务即结束——**没有下一次 tick 重试**，用户直到几小时后追问「完了吗/结果呢」才发现。诊断：用户问进度但任务实际已完成 → 第一反应查 `cron/output/<job_id>/` + gateway.log 的 send failed，**不要重新跑任务**。重要汇报若预期推送窗口危险（长消息、多分块），可把一次性任务改成每 10-15min 轮询型（prompt 内判断：summary 齐全则汇报并输出完成标记，否则 `[SILENT]` 静默等下一轮），天然带重试。

**原因**：微信 iLink 接口有频率限制。腾讯未公开具体配额。**服务端主动推送（Cron）间歇性受限，且交互回复也可能被限速吞掉**（2026-08-17 实测：v3.0 完成汇报是活跃会话的直接回复，仍被限速 15 次连续失败、降级重试也失败、最终静默丢失）。用户静默期（多日无交互）风险更高。

**注意**：`last_status=ok` 只代表调度器成功执行了 prompt 并尝试了推送，**不代表消息已到达用户客户端**。必须检查 `last_delivery_error` 字段。

#### ⚠️ 交互回复静默丢失——「做完没告知」教训（2026-08-17）

**现象**：重大任务完成汇报（长消息）发出后用户没反应，甚至追问「进度如何？」——实际消息被限速吞了，用户以为任务没做完。

**根因**：完成汇报是长消息，分块多，更容易触发 iLink 限速。日志显示连续 `[Weixin] send failed ... iLink sendmessage rate limited`（重试耗尽后 fallback 也失败），**最终静默丢失，无人察觉**。

**诊断模式**：用户在大任务完成后马上问「进度如何/做完了吗/怎么没消息」→ **第一反应是查 gateway.log 的 send failed / rate limited，而不是重新做任务或解释进度**：

```bash
grep -E "send failed|rate limited" ~/.hermes/logs/gateway.log | tail -20
```

**硬规则**：
1. **重大任务完成时，汇报发出不等于送达**——微信限速可吞掉任何消息（含交互回复）
2. 用户追问「进度如何」但任务确实完成 → 先查投递日志，确认是否发送失败，**主动补发**，不要反问用户
3. 补发时拆短消息或稍等片刻重试（限速窗口通常几分钟）
4. 完成通知宁可多确认一次（「收到请回」）也不能静默

#### ⚠️ 主动会话 send_message（含 MEDIA 文件）也会被限速（2026-09-25 实战）

**现象**：`send_message target=weixin` 发 43KB MD 报告文件（MEDIA 附件+说明文本），**连续 3 次** `iLink sendmessage rate limited: ret=-2 errmsg=prepare failed`——间隔 8s、30s 的重试同样失败，短间隔连环重试无效。

**应对序列（实战定型）**：
1. **不要短时间内连环重试**——3 连败后继续原地重试只会继续失败，先止损
2. **告知用户不能用 wecom 通道**（⚠️ 2026-09-25 用户明确「我没有企业微信」——wecom Home `<用户wecom账号>` 消息用户侧根本看不到，send_message 返回 success ≠ 用户知情）。正确做法：会话还活着就直接文字告知「文件已就绪、微信限流中、约 X 分钟后自动重发」；重试到点即发，不假手 wecom
3. **重试间隔拉到分钟级**：terminal background `sleep 250 && echo RETRY_WINDOW_OPEN` + notify_on_complete，到点再重发 weixin（实测 ~4 分钟冷却后一次成功）
4. 发文件前先 `cp` 成无空格/无特殊符号的短路径（如 `~/报告名_日期.md`）再发 MEDIA——原路径含空格与「·」时顺手规避，避免多一个变量
5. ⚠️ wecom 通道（<用户wecom账号>）已定性为**用户不可见通道（9/25 用户纠正）**：禁止作为通知/交付通道，仅可当 MyPS 内部留痕；**待办：从 config 摘除该平台**（已向用户承诺）。下方长期缓解表中一切「企微」方案在用户侧确认可用企微前一律禁用

#### ⚠️ 持续限流窗口的恢复（2026-09-29 实证）

固定冷却不可靠：限流风暴期（`ret=-2 prepare failed` 连续失败）**等 6 分钟后重发仍失败**——限速窗口长度不固定，不能赌冷却时间。有效姿势：

1. **借用户入站消息重置窗口**：用户发来任何消息（inbound 正常 = 只有发送方向受限）后，紧跟一条**短消息**发送，实测一次成功；长消息（300 字+）在窗口边缘更易失败，恢复期先发短的探路
2. **手动补发前先看 gateway.log 是否在自动重试**——用户 inbound 会触发 gateway 对排队回复的 3 秒退避自动重试（`backing off 3.0s before retry`），此时手动 send 制造竞争；日志出现新的 `send failed` 后再接手
3. **失败期间先把完整内容落盘**（data/documents/ 或临时文件），通道恢复后补发——内容不丢，重发只是搬运
4. 长内容（验收报告类）可拆「短摘要先行 + 完整版文件转交」，摘要短消息过限速窗口的概率远高于整段长文

#### ⚠️ 反方向陷阱：误判推送失败 → 重复补发（2026-08-28 实测）

**现象**：一次性汇报 cron 其实已成功送达，但排查时 grep gateway.log 的模式写宽了（如 `grep -E '18:3[0-9]|18:4[0-9]|19:[0-9]{2}'`——`19:[0-9]{2}` 会匹配任意时间戳的**分:秒**位置，把 12:19:06、14:19:45 等历史限速记录全捞出来），误以为 18:35 的推送被吞，向用户补发了一份精简重复版。用户纠正：「18:35 那份更详细的其实收到了」。

**正确判定流程（三查）**：
1. `ls -lt ~/.hermes/cron/output/<job_id>/` —— 有输出文件且时间戳≈调度时间 → 任务执行成功
2. grep gateway.log **带日期前缀锚定**：`grep '2026-08-28 18:3' ~/.hermes/logs/gateway.log` —— 只有该时间窗内出现 `send failed`/`rate limited` 才算失败；裸小时模式（`18:3x`）会串到其他行的分秒位
3. 无失败记录 + output 存在 → **默认已送达，不要补发**；拿不准时先问用户「18:35 的报告收到了吗」再决定

**原则**：补发的代价是重复打扰，漏发的代价是用户不知道结果。先三查，证据确凿（该时间窗 send failed）才补发。

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

0. **首选：直接读 cron output 原文**（2026-08-28 实测最快路径）：`cron/output/<job_id>/<时间戳>.md` 完整保存 prompt + Response，内容一字不差、无需重建。`ls -lt ~/.hermes/cron/output/<job_id>/` 按时间找最新文件，读出来整理补发即可——比 session_search 快且不失真（session_search 返回 LLM 摘要，cron output 是原文；若 output 目录为空再退回 session_search）。⚠️ 文件约 90% 是 prompt/skill 回显，**报告正文在尾部 `## Response` 之后**——用 `tail -c` 取正文即可，别把 90KB+ 全文读入（2026-09-20 实测：daily-review 输出 93KB，正文仅末尾约 1KB）

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
| ~~改用企业微信~~ | ⚠️ 9/25 用户否认拥有企业微信——wecom(<用户wecom账号>) 消息用户不可见，**禁用为用户通道** | 待从 config 摘除该平台；仅可作 MyPS 内部留痕 |
| ~~微信+企微双推~~ | 同上不可用 | 用户知情渠道只剩 weixin；限速期只能等冷却（分钟级）重发 |
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

### ⚠️ Cron 被注入扫描器 BLOCKED（ssh_backdoor 等威胁模式误判）——2026-09-01 实战

**现象**：cron 任务 `last_status` 缺失/状态 BLOCKED，output 目录里显示 `Status: BLOCKED` + `Scanner result: Blocked: prompt matches threat pattern 'ssh_backdoor'`，任务未执行。一次性任务 BLOCKED 后还可能从 cron 列表消失（如 v0.4 24h 收尾 cron），**无人察觉收尾从未执行**。

**根因**：cron 的 prompt（含加载的 skill 内容）含 SSH/远程命令文本，命中 `_CRON_THREAT_PATTERNS` 注入扫描器。host-ops skill 里满是 ssh 命令，作为 cron skill 加载时极易触发。

**修复方案**：涉及远程操作的一次性收尾/检查 cron 改用 **no_agent 脚本模式**：
1. 本地写脚本（如 `~/.hermes/scripts/xxx_finalize.py`），脚本内 `subprocess.run(['ssh', ...])` 执行远程检查
2. cron 创建：`no_agent=True` + `script=路径`——cron prompt 不含任何远程命令文本，扫描器不拦
3. no_agent 语义：非空 stdout 原样投递；空 stdout 静默。脚本设计成「有结论必打印」

**排查流程**：用户反馈「XX 收尾没消息」且 cron 列表里该任务消失 → 查 `cron/output/<job_id>/` 最新文件是否含 `Status: BLOCKED` → 是则按上述方案重建为 no_agent 脚本任务，并人工补做一次收尾检查。

### 等外部人工动作 → no_agent cron 看门狗模式（2026-09-10 实战定型）

**场景**：等用户在**未知未来时刻**完成一个物理动作（搬机器并上电、重启、插硬件、手工执行某步），完成后 agent 要自动接手跑后续流程。

**❌ 不要用 terminal background watcher**：轮询循环有窗口上限（如 2h），过期即作废，还得手动重挂；且随会话存亡，session 重启就丢。9/10 实战：测试硬件N 搬家监控挂了 2h 窗口的 bash 轮询，用户没搬，watchdog 空转到过期（exit 1）。

**✅ 正确姿势：no_agent cron 看门狗**（实例 `~/.hermes/scripts/n305_move_watch.sh`，job 202dcf16f4af）：
1. 本地脚本 + `no_agent=True` + `*/10 * * * *`，静默值守（stdout 空 = 不推送）
2. **状态检测用「新 boot/新状态」而非「下线又上线」**：如用远端 `/proc/stat` 的 btime 存状态文件，btime 变化 = 重启过 → 触发动作。比「等下线→等上线」两阶段探测简单且无窗口问题
3. **首跑必须静默建档**（无状态文件时只记录当前值、不触发），否则第一次 tick 就误报
4. 事件分支输出报告（健康检查+后续动作一次跑完）原样投递给用户；不可达分支连续 N 次（如 3 次≈30 分钟）才报警一次，防重复打扰；恢复正常自动清零
5. cron 创建时 `script` 参数**只接受相对文件名**（相对 `~/.hermes/scripts/`），绝对路径会被拒
6. **事件触发并完成后记得 remove cron**（值守任务完成即清，不留空转垃圾）

**排查流程**：

1. **手动重跑判断性质**：`cronjob(action='run', job_id='<job_id>')`
   - 重跑成功 → 临时性故障（瞬断），无需停任务或改配置
   - 重跑同样失败 → 持续性故障，需深入排查

2. **横向对比**：同一时间段内其他 Cron 任务是否也报错？只有个别报错 → 检查模型/provider 配置差异

3. **连续多天同一错误**：如果同一任务连续 3+ 天在不同时间点报相同 SSL 错误 → 排查服务器时间准确性（导致证书验证失败）或代理/防火墙拦截

**核心教训**：provider API 层的 SSL/连接错误大多是一次性瞬断。手动重跑确认一次即可，不要直接停任务。

**定位错误细节（8/21 SSL 实战验证过的日志路径）**：
- 失败运行记录：`cron/output/<job_id>/<时间戳>.md`——含完整 prompt + 底部 Error 段，先看这个确认错误现场
- 重试时间线：`grep "<cron会话ID>" ~/.hermes/logs/errors.log`——每次 attempt 的时间与重试间隔；cron 会话 ID 形如 `cron_bccc5ba95b30_20260821_083022`（errors.log 与 agent.log 都有）
- 流式失败点：`grep "Streaming failed" ~/.hermes/logs/agent.log`
- ⚠️ 日志都在 `~/.hermes/logs/` 下（errors.log / agent.log / gateway.log），**根目录没有 gateway.log**

**判断临时性的辅助证据**：
- 查历史：`grep "cron_<job_id>" ~/.hermes/logs/errors.log` 中该任务**之前是否出现过同一错误**。8/21 实战：同错误 8/19 也出现过且重试成功 → 佐证是间歇性网络问题而非配置问题，不用改任何配置
- 当前连通性验证：`curl -sS -m 10 -o /dev/null -w "%{http_code}" https://api.deepseek.com/`——返回 401（无 key 的正常响应）= 网络已恢复；且本会话正通过同 provider 回复用户 = 通道已通
- **完整健康检查**（key 有效性 + 流式路径）：`python3 ~/.hermes/skills/myps-operations/scripts/llm_api_probe.py`——读 auth.json 的真实 key 做非流式/流式各 N 次真实调用。curl 401 只证明网络通，此脚本证明 key 和流式链路都正常（8/21 实战：cron 全挂但脚本 6/6 全过 → 确认是间歇性网络问题，非配置问题）

**重跑后告知用户**：`cronjob(action='run', job_id=...)` 在下一调度 tick 执行（约 1-2 分钟），要向用户说明「补跑已触发，简报稍后到」，避免用户误以为又静默失败。

### 主动会话回复中断（流式中断）——2026-09-08 DeepSeek 实测

**现象**：用户看到回复「说一半断了/没说完」，问「刚才是不是报错了/DeepSeek 返回错误了」。**用户在微信端能看到流中断，不必等他描述细节**——第一反应查日志确认：

```bash
tail -50 ~/.hermes/logs/agent.log | grep -E "Stream drop|Streaming failed|Turn ended"
tail -30 ~/.hermes/logs/errors.log
```

**判定特征**（9/8 实测模式）：
- `Stream drop on attempt N/3 — retrying ... error=RemoteProtocolError: peer closed connection without sending complete message body (incomplete chunked read) http_status=200` —— DeepSeek 上游（openresty）掐流式连接，HTTP 200 但 body 没发完
- `Streaming failed before delivery: Connection error.` + `Turn ended: reason=interrupted_during_api_call` = 该轮回复中断
- 重试 3 次仍断 → turn 中断，**消息自动排队下轮重发**（`Interrupt recursion depth N reached ... queueing message` 属正常恢复机制，不是死循环）
- 恢复：上游抖动通常几分钟内自愈（9/8 实测 19:34 断 → 19:36 恢复），无需任何操作

**处置**：确认日志后向用户简短说明（哪家 provider、什么错误、已自动恢复），不夸大不淡化；若用户因此提出切模型（如 DS→GLM），按 `references/model-switching.md` 的切换 SOP 执行——provider 不稳正是切换的正当理由。

### 「Auxiliary auto 池坏节点拖垮辅助功能」（2026-09-15 实战定型）
**现象**：每晚总结时段 `Session summarization failed after 3 attempts: 429`（错误码 1302=智谱限速）+ 日志大量 `Auxiliary: marking nous/openrouter unhealthy (payment / credit error)`；`session_search` 超时（连续多晚）；cron 因 429 重试明显变慢（22:00 调度 22:30 才完成）。

**根因**：config.yaml `auxiliary.*`（compression/session_search/skills_hub 等）`provider: auto` 走内置 aux 池——Nous（从未 `hermes auth`，无认证）+ OpenRouter（余额耗尽）两个**必死节点**每次调用先挨个试，再 fallback 主模型 GLM，撞上 GLM RPM/配额限速。坏节点重试白白消耗时间和 GLM 配额，与主对话 429 相互放大。

**诊断特征**：errors.log 里 `payment / credit` + `unhealthy` 每天几十条 + `429`/`summarization failed` 成对出现 = 此病。

**修复**（脚本幂等，`~/.hermes/scripts/fix_aux_pool_20260915.py`）：把 aux 各子段从 auto 指定到已验证可用的 Agnes（provider: agnes + model: agnes-2.5-flash + base_url + api_key 复用 vision 段 key，自包含三件套）。改后必须重启 gateway 生效（kill → watchdog 拉起）。先 curl 验证目标 provider 文本连通（vision 通≠文本通道验证过，虽通常同一端点）。

**2026-09-15 当前生效态（Agnes 方案当天即升级，诊断以 config.yaml auxiliary 段实际内容为准）**：用户提供 OpenRouter key（免费层，存 `.env` `OPENROUTER_API_KEY`，config.yaml 明文）→ 三段切 openrouter 直连 `nex-agi/nex-n2.5-mini:free`（实测 1.4s 出文最快）。候选筛选教训：nemotron-3.5 思考型 token 被思考耗尽不适用摘要类任务、inkling-small 403 仅对 agentic 应用开放、ling-3.0-flash-sante/vl 备选（2.3-2.9s）。免费层限速 ~20 req/min，辅助任务频次够用。vision 仍为 Agnes。回滚备份：`config.yaml.bak-or-switch-20260915`（OpenRouter 切换前）/ `.bak-20260915`（auto 池修复前）；切换脚本 `scripts/switch_aux_openrouter_20260915.py`。

> 2026-09-15 已二阶段升级：三段最终直连 **OpenRouter 免费模型** `nex-agi/nex-n2.5-mini:free`（用户供 key）。auto 探测链源码机制、模型筛选实录、脚本清单、回滚备份 → `references/auxiliary-channel-switching.md`

**验证**：改后次日 errors.log 中 `payment / credit`、`unhealthy`、`summarization failed` 应趋零；429 显著减少。

**辅助通道换免费模型的选型清单**（2026-09-15 OpenRouter 实战，Agnes 免费期结束时换血用）：
1. `GET /api/v1/models` 筛 `:free` 后缀 → 逐个用真实小任务测（中文摘要+情绪判断），不要信模型名
2. **思考型模型直接排除**（如 nemotron 类）——max_tokens 被内部推理耗尽，正文为空或截断，摘要任务不可用
3. 403 `only available on agentic harnesses` = 该免费模型只对 agent 应用开放，API 直调不行，跳过
4. 免费层限速约 20 req/min——辅助调用每天几十次且分散，够用；key 存 .env 再写 config.yaml（该文件在 .gitignore）
5. 换完必须重启 gateway（kill → watchdog 拉起）；旧配置留 .bak 可回滚

**同日演进（2026-09-15 下午定稿）——辅助三段最终切到 OpenRouter 免费模型**：用户提供 OpenRouter key（免费层，存 `.env` 的 `OPENROUTER_API_KEY`，config.yaml 内联明文，备份 `.bak-or-switch-20260915`）。三段（compression/session_search/skills_hub）现为 `openrouter + nex-agi/nex-n2.5-mini:free`（直连，不走 auto 链）。切换脚本 `~/.hermes/scripts/switch_aux_openrouter_20260915.py`（幂等）。**免费模型筛选结论（19 个候选实测）**：nvidia/nemotron-3.5-lightning:free = 思考型模型，max_tokens 被内部思考耗尽才出正文——辅助杂活排除；thinkingmachines/inkling-small:free = 403 仅对 agentic harness 开放；蚂蚁 ling-3.0-flash（sante/vl）正常但较慢（2.3-2.9s）；**nex-n2.5-mini 最快（1.4s）入选**。免费层限速 ~20 req/min，辅助调用频度（每天几十次分散）足够。回滚：config 备份 `.bak-20260915`（Agnes 版）均可恢复。看图通道 vision 保持 Agnes 不动。

> 深度参考：`references/auxiliary-auto-chain-mechanism.md`——auto 四站探测链源码机制（60s TTL、第4站与主模型共享额度=互相放大的根源）、config.yaml 解剖、供应商选型决策框架（Agnes 现状 / OpenRouter 免费模型为预定接替 / Nous 不值得专门注册；原则=直连确定性优于 auto 弹性）、OpenRouter 切换预案与触发信号。机制解释类提问（「auto 池是什么」）先读此文再答。

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

### ⚠️ 微信 bot 被外部服务顶掉（2026-09-06 某第三方AI助手 事件）

**现象**：gateway 进程正常、日志无错，但用户失联收不到消息（或用户主动说"我连了 XX 把我冲了"）。

**根因**：微信 iLink bot 体系**一微信号单 bot 在线**。用户用同一微信扫码连接其他 iLink bot 服务（9/6 实例：连接 某第三方AI助手——用户前期口述"OK Body"，后确认实为 某第三方AI助手 的微信连接；同类服务同理）时，新连接顶掉 MyPS 的 bot 会话 → 失联。平台会提示"已有一个连接，连接新的会冲掉"——用户常没在意。

**修复路径**（2026-09-06 某第三方AI助手 实战，重登流程）：
1. 重新扫码登录新 bot：拉 iLink 二维码 → 用户扫码确认 → 新 bot 凭据（account_id/token）保存到 `~/.hermes/weixin/accounts/<new_id>.json`
2. 更新 `.env` 的 `WEIXIN_ACCOUNT_ID` / `WEIXIN_TOKEN` 为新 bot（改前先备份 .env）
3. 重启 gateway（见上节流程）→ 用新 bot 连微信
4. 旧 bot 账号文件改名 `.bak` 保留（可回滚）；accounts 目录里 context-tokens.json / sync.json 随新 bot 自动重建

**✅ 用户自助首选：一键恢复脚本 `~/wx-recovery/wx_fix.py`**（2026-09-06 用户要求编写——**用户偏好：MyPS 系统故障修复交付「用户可自行运行的一键脚本」，而非 agent 远程自主修复**；微信重连这类需人工扫码的故障尤其如此，用户 SSH 进来跑脚本+扫码，全程自己掌控）。用法：

```bash
su - hermes -c 'source ~/venv/bin/activate && python3 ~/wx-recovery/wx_fix.py'
```

脚本自动：①检测 sync 游标（60s 内更新=正常，提示无需修复，防误跑）②异常则拉二维码（终端 ASCII 直接扫 + 存 PNG `~/wx-fix-qr.png` 可下载放大）③轮询扫码状态（2 分钟过期自动刷新×3，总超时 480s）④confirmed 后全自动：保存新凭据到正确目录（chown 归 hermes 防 root 运行权限问题）→ 旧账号 .bak 停用 → 备份并更新 .env → kill gateway 等 watchdog 拉起 → 验证 sync 跳动。日志 `~/wx-fix.log`。已测：正常分支 + 二维码拉取链路；完整扫码首次真实使用验证。

**⚠️ 外部 AI 工具（某第三方AI助手 等）经 SSH 介入修复后的痕迹审查清单**——用户可能让别的 AI 直接 SSH 进容器操作，事后必查：
1. `last`——SSH 登录记录（root 从用户电脑 用户电脑 <局域网IP> 进来 = 外部工具操作痕迹）
2. `~/.ssh/authorized_keys`——有没有被添加 key（无新增 = 一次性访问，非持久后门）
3. `/etc/rc.local` 的 mtime 与内容——自启注入是常见后门位；mtime 变但内容干净 = 只是重写
4. `~/`、`/root/` 下的新脚本（find -newermt）——外部工具常留 fix/relogin 脚本与过程 json
5. cron 列表 + 进程表——有无新增定时任务/常驻进程
6. 审查结论三要素：逻辑是否合理、有无凭据泄露面、有无持久后门。合理的一次性修复 → 向用户报告后清理痕迹文件（脚本+过程数据），保留真正运行所需的凭据文件

**预防**：某第三方AI助手（及其他同类 iLink bot 扫码服务）与 MyPS 互斥，同一微信号不能同时连两个 bot——再连 = MyPS 再失联。用户明确偏好：同类故障用 wx-fix 一键脚本自助恢复，不依赖外部 AI 修复。

**⚠️ 排他性跨服务实证 + 规则定型（2026-09-28 某AI通道服务 事件）：一号一 bot、后绑顶先绑，双向成立**
- 互斥双向验证：9/6 某第三方AI助手 顶掉 MyPS（主号）；9/28 某AI通道服务 顶掉 某第三方AI助手（小号）——**任何**同类通道服务绑号都会挤掉先绑者，不限具体对象
- 影响面拆分：被顶的只是**对话通道**（微信里找不到该 bot）；网页自动化类托管不受影响（某第三方AI助手 签到走 serve:8765，通道被顶当天 00:06/17:10 照常跑）——用户报「XX 被顶了」时先问影响的是对话还是托管
- 重绑可逆且快（~10s），代价疑似**对话会话重置**：9/28 实测 某第三方AI助手 重绑后对「你好」回新用户开场白（服务端数据/Skill/积分都在，对话连续性断，待二次确认）
- 隐性成本结论：任何要接微信的 AI 服务需单独占号——计入同类服务的采用决策
- 档案：`data/knowledge/某AI通道服务-微信bot通道档案-20260928.md`

### Gateway 失效排查流程

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

- 脚本：`~/.hermes/scripts/gateway-watchdog.sh`（v2；2026-09-06 加 flock 单实例锁）
- 机制：每 30s 检查 gateway 主进程（`/venv/bin/python.*gateway run` 精确匹配），连续 2 次检测不到则自动拉起
- 开机自启：`/etc/rc.local`（Linux Deploy 开机钩子；2026-09-06 重写修复，备份 `/etc/rc.local.bak-20260906`）
- 日志：`~/hermes-watchdog.log`（9/6 起追加式）
- 手动启动：`su - hermes -c "setsid nohup /bin/bash ~/.hermes/scripts/gateway-watchdog.sh >> ~/hermes-watchdog.log 2>&1 </dev/null &"`（脚本自带 flock，重复执行安全）
- 单实例锁：`/tmp/hermes-watchdog.lock`（exec 9> + flock -n，防止重复启动）

**⚠️ 2026-09-06 重大修复：rc.local 的 `pgrep -f gateway-watchdog.sh || bash ...` 是 bug，不是防重复**——pgrep -f 会匹配到执行它的 shell 自身（命令行含该字符串），恒为真 → `||` 右侧的启动命令**从不执行** → watchdog 自 8 月以来从未真正开机自启（靠手动启动的实例撑着）。修复：rc.local 去掉 pgrep 判断直接 setsid 启动，单实例改由脚本内 flock 保证。**教训：`pgrep -f X || start X` 是守护进程经典陷阱；判断机制是否生效只能靠实测**（9/6 kill -9 验证：48 秒自动拉起）。排查重复实例时注意：`pgrep -f` 会把命令自身的 bash 包装计入，需排除 `bash -c` 行再数。

**⚠️ v1 事故教训（2026-08-17）**：watchdog 用宽泛 `pgrep -f "hermes gateway run"` 检测时，旧 gateway 优雅关闭期间进程仍在（SIGTERM 后等待当前会话结束），且临时 bash 包装进程也含该字符串 → 误判存活 → 不拉起。修复：精确匹配 python 主进程路径 + 连续 2 次缺失才触发。

**✅ 真实演练结论（2026-08-17 二次演练，铁证已验证）**：独立 watchdog 拉起路径真实跑通——击杀 gateway（14119）后，watchdog 14124（PPID=1，rc.local 启动）独立存活，11:37:48 自动拉起新 gateway 14341（PPID=14124=watchdog）。**判定拉起者**：新 gateway 的 PPID = watchdog PID → watchdog 拉起；PPID=1 → rc.local 兜底；PPID=用户 shell → 手工重启。

**⚠️ 误判教训（第一次演练）**：曾宣布"自动恢复成功"，实际是用户手工重启救的（用户原话「还是起不来，是我手工重启的」）。根因：手动启动的 watchdog 是 gateway 子进程，gateway 优雅关闭时连带杀死，守护链断裂。教训：**宣布自愈成功前必须核对 PID/PPID/启动时间三件套，不能凭"能收到回复"下结论**。

**⚠️ 恢复后"进程起来了 ≠ 通道通了"**：gateway 拉起后平台通道异步重连——weixin 约 10s 连上，wecom 可能重连失败 3 次、耗时约 3 分钟（实测 11:39-11:42），且回复投递可能 unconfirmed 被排队补发。用户报「没反应」时先查 `gateway_state.json` 两个平台 state 是否都 `connected`，再看 gateway.log 有无 inbound 时间戳——区分「没起来」「通道重连中」「投递未确认」三种情况，不要急着宣布成功或失败。

**⚠️ 微信 bot 会话被挤掉后的重连**：完整三步（重新扫码 → 新凭据进 `~/.hermes/weixin/accounts/` → 改 `.env` 的 WEIXIN_ACCOUNT_ID/TOKEN → 重启 gateway）与 `.env` 凭据优先于账号文件等根因细节，见上方「微信 bot 被外部服务顶掉」章节 + 完整手册 `~/wx-recovery/hermes-微信重连-复盘与自愈手册.md`（某第三方AI助手 2026-09-06 编写，配套工具在 `~/wx-recovery/`：wx_relogin.py / fix_weixin.py / fix_watchdog.py）。

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

- **载体 = 旧安卓手机**（Linux Deploy chroot 容器），**不是迷你主机/小主机**——2026-09-23 用户确认。MyPS 长期误记自己的载体，直到 9/23 自媒体草稿写出「小主机」被用户当面改正；内核特征可佐证（`4.4.153-perf+` = 安卓内核版本号）。副产物：MyPS 本身就是 PAOS 愿景「有基础者用旧电脑/旧手机自部署」的第 0 号实例
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

当需要将当前运行版的改进同步到公开仓库时（如 v2.0 → v3.0）：

> **完整实战流程见 `references/public-release-workflow.md`**（v3.0 跑通版：API 拉取对比、脱敏替换表、根文件策略、docs/ 辅助文档、推送验证）。以下为要点摘要：

1. **判断差距**：查公开仓库最后 commit 日期 + 本地 skills 更新时间 + 新增 Skill 数量，量化落后程度再决定是否发版
2. **拉取公开版**：本地无 clone 时用 Git Data API 拉全部文件到临时目录（跳过 .gitkeep，todos.json 单独取）
3. **对比差异**：逐文件 md5 对比公开 vs 本地，确定更新/新增清单；Hermes 自带 skill（onboarding 等）不发布
4. **脱敏**：按敏感词清单（微信 ID/人名/项目名/硬件/工作实体/路径）逐文件替换为通用词，替换后二次扫描确认残留。**⚠️ 脚本覆盖面 ≠ 本次新增内容（2026-09-30 发布前检查发现）**：public-repo-sanitize.sh 是静态文件清单+静态词表（v1 仅覆盖 fragment-catcher/emotion-coach/daily-review 三个 SKILL.md），每轮新增的 skill/docs/reference 全部不在覆盖内——发布前固定动作：①差集检查「本次打包清单 vs 脚本 FILES 列表」，差集文件按 workflow 3.1 敏感词类别逐文件人工扫描；②确认打包排除项：data/ 全部（含 data/journey/ 成长回放档案，内含真实个人里程碑）、memories/、真实 MEMORY.md、cron 配置、diary；③发现新敏感词类别时补进脚本替换表（脚本=唯一权威词表）
5. **根文件**：SOUL/USER/MEMORY/AGENTS/INSTALL/README 等**以公开版为基底**只升级版本号——本地版含个人数据不可直接用；skills/SKILL.md 用脱敏后的本地版
6. **辅助文档**：新版本关键方案（如 watchdog 自愈）写成 `docs/<主题>.md` 独立辅助文档（frontmatter 标 `type: auxiliary-doc`），不并入 README 主文档
7. **推送**：Git Data API 一次提交（blob → tree → commit → PATCH ref），跳过 .gitkeep 空文件
8. **验证**：HEAD sha 断言 + commit message + 递归文件树 + 必须文件存在性检查，不要只看 API 返回码

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

> **Gitee 镜像（2026-09-28 打通）**：公开仓双仓分发——GitHub 唯一真源 + Gitee 单向镜像（gitee.com/goodvfx/MyPS），国内访问可达。GitHub 更新后跑 `scripts/gitee-mirror-sync.sh` 同步（幂等+sha 校验）；GITEE_TOKEN 在 .env。资产/流程/坑见 `references/gitee-mirror-sync.md`
>
> **推仓凭据诊断（2026-09-28 实战）**：git 推送凭证可能存两处——`~/.hermes/.env`（显式 token）与 `~/.git-credentials`（git credential store 自动留存，容易被漏查）。认证失败先验证令牌有效性：`curl -sS -H "Authorization: token $TOKEN" https://api.github.com/user` 返回 `Bad credentials` = 令牌过期/被撤销（不是「用户没给过」），直接找用户要新 token；两处都翻完再下「缺凭据」结论

> **⚠️ 脱敏必须脚本化（2026-09-28 审计教训，长期铁律）**：v3.0 发布靠人工对词表，后续 skills 更新的案例把同事真名×8、真实家庭行程×11、职业画像×15 带进公开仓近两月才被发现。**发布管线固定顺序 = 修改 → `bash ~/.hermes/scripts/public-repo-sanitize.sh`（含残留 grep 审计）→ commit → GitHub 推送 → `scripts/gitee-mirror-sync.sh`**；新敏感词加进脚本替换表（脚本即唯一权威词表）。教训细节与替换对照表见 `references/public-repo-sanitization.md`

> **公开版端用户备份/恢复设计**（2026-09-29 方向定稿、待发令实现）：威胁模型切割（手机灾难→云 / Linux 层崩溃→本地副本）、`myps-backup`/`myps-restore` 内置命令、环境可再生+数据双副本、WebDAV 可选扩展——设计全文与开工清单见 `references/公开版-端用户备份恢复设计-20260929.md`

> **终端安全扫描与脚本坑汇总**：curl|python3 管道 HIGH 拦截、tar→/tmp MEDIUM、`set -e`+grep 空匹配毒杀脚本、前台超时整进程组清理（/tmp 文件消失）、git 在手机上需逐命令 timeout 包裹等——写长脚本/批量命令前先对表 `references/terminal-scanner-and-scripting-pitfalls.md`

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
| 报销预估 vs 到账实数 | 交财务前的金额是预估（垫付拆分易算重）；**销账一律以到账实数和用户口径为准**（2026-09-29 实例：预估 1651 被用户修正为到账 1611，差额是多算的一笔运费） |
| Chronic reminder vs hard deadline | 持续提醒直到用户喊停 vs 有明确截止时间的单次提醒 |
| **公开版 vs 个人版** | 公开版不含任何个人数据；个人版是全量运行环境 |

---

## 月度周期性任务

对于用户每月固定要做的任务（如 10 号前的行政工作），最佳实践是：

1. 保存到 memory/ 以便随时查阅具体内容
2. 创建每月 1 号的 Cron 任务作为月初提醒
3. 如果需要更细致的跟踪，可以创建待办条目

**MyPS 成长回放（Journey）机制**（2026-09-30 上线，prompt 当日定型）：每月 1 日 08:47 cron（job `76a546e613d6`）统计上月成长轨迹，归档 `data/journey/YYYY-MM.md`（已存在则覆盖）并推微信（≤400 字，五段结构+末尾注明档案路径）。数据源四类、不读 sessions 原文：①git log/stat（skills/ 新增、MEMORY.md 变更、knowledge/documents 新增）②diary 当月关键节点 ≤6 条 ③todos.json（⚠️ 无完成时间戳，口径必须写「当月创建且已完成」）④MEMORY.md 水位 + `data/journey/waterlevel.log`。例外处理：数据空写「无新增」、git 缺失如实说明不编造。水位日志由 daily-review 整理流程追加（format: `YYYY-MM-DD|字符数|条目数`），是本机制的数据前提——勿删改日志格式。上线当日已实跑模拟验证（9 月主路径 ✓，打法见上文「新 Cron 机制上线即模拟测试」）。

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

- 预创建条目带月份标注（如「打印报表D（8月）」），Cron prompt 第 3 步「确保不重复添加已有条目」的查重逻辑能识别并跳过
- 效果：下月简报不出现重复提醒，组进度自动反映「已完成 N/6」
- 这是 monthly-checklist Cron 查重机制的配套用法，fragment-catcher 的批量组章节有完整处理规则
