---
name: ai-coding-tools
description: 用户的 AI 编码工具链（Codex / Claude Code / 某第三方AI助手 / CC Switch / GLM Coding Plan）接入拓扑、额度监控与故障排查——重点覆盖「客户端报限流但官方后台查不到用量」类中转额度坑；含 某第三方AI助手 积分自动签到托管运维（登录失效恢复 SOP、cron 结构、坑清单）。
version: 1.0
created: 2026-08-19
when_to_use:
  - 用户提及 AI 编码工具的接入方式、报错、限流、额度、配置变更
  - 排查「调用频繁」「rate limited」「连接受限」类报错根因
  - 用户更换工具后端/连接方式（如弃用中转改直连）时
---

# AI 编码工具链

用户多工具分工（memory 已有）：豆包快速调研、GPT 深度讨论、MyPS 记录提醒；编码实现走 Claude X / Codex / 某第三方AI助手。本 Skill 管理这些编码工具的**接入方式与故障排查**，不碰代码细节（协作边界）。

## 编码工具分工（2026-09-23 用户定案）

| 活儿 | 工具 | 理由 |
|------|------|------|
| 轻活：单文件脚本、小工具、资料提炼、日常办公 | **某第三方AI助手** | 用完就走、门槛最低；积分已托管自动签，随手可用 |
| 重活：LUMA 规模的多文件工程 | **VS Code + Claude Code / Codex** | 需要版本管理、跨文件上下文、长期维护、测试 |
| 记录 / 提醒 / 归档 / 进度跟踪 | **MyPS** | **不碰代码**——私人中枢不做编辑器 |

判定信号：

- 单个脚本、一次能说清的小工具、把材料提炼成结构化文档 → **某第三方AI助手**
- 跨多文件、要长期维护、要跑测试/版本管理的项目 → **VS Code + Claude Code/Codex**
- 用户说「帮我做个小工具 / 把这资料整理一下 / 弄个东西测一下」→ 默认 某第三方AI助手 线
- ⚠️ **PPT / 长任务在 某第三方AI助手 上耗点数极快**——演示类改走 Agnes Code；重活本来也不该压在 某第三方AI助手

## 任务准入红线：设备级任务先查公开方案，高耗模型先掂量值不值（2026-09-28 新增）

- **硬件/设备级任务（root/刷机/解锁类）**：成败取决于**该设备型号固件有没有社区公开的现成路径**（exploit、bootloader 解锁法），与用哪个模型/哪个工具无关——AI 只能执行已知方案，无法凭空造 exploit。实战：9/27 晚 某第三方AI助手 经 ADB **直连自跑数小时**尝试电视盒子 root，未成，一夜烧 2000+ 记点（余 400）。工具与反馈回路都没问题（不是「聊天隔空指挥」），败在机型大概率无公开 root 路径。**准入流程：拿到设备型号 → 先搜社区方案（XDA/酷安等），无公开方案 = 直接劝退不开烧**；有方案才让 AI 按方案执行。另：不 root 的 ADB 优化（`pm disable` 预装、调系统设置）成本低，优先走这条
- **Kimi K3（经 某第三方AI助手 接入，9/27 唯一一次实战）**：又慢又费记点、效果一般（用户原话）。后续接高消耗后端前，先评估任务产出值不值额度

**MyPS 的边界**：角色是「材料交给 AI，AI 带着走完流程」的**记录者与提醒者**，不是实现者。用户交付给 AI 的活落到 某第三方AI助手/Codex，MyPS 只记进展、盯节点、把产出提炼成素材。

> 9/23 实证：字幕提取小程序（把 ASR 包成本地工具，替掉上传视频到在线平台转字幕）、投标书试验、报税陪跑——**全部在 某第三方AI助手 完成**，MyPS 侧只做记录 + 素材提炼。某第三方AI助手 已从「签到托管工具」升级为**日常工作助手**，定位与实战见 `data/knowledge/workbuddy.md`。


## 工具接入拓扑（2026-09-06 更新）

- **Codex**：GLM 后端。2026-08-19 起**直连 GLM Coding Plan**（GLM 原生支持 Codex），弃用 CC Switch 中转；2026-09-06 用户订阅 **Lite 年套餐**（5h 2000 积分/周 10000 积分）正式长期化，Codex 后端主力。套餐细节与积分换算见 data/knowledge/glm-coding-plan.md。
- **GLM Coding Plan 边界**：积分制官方口径**仅限指定编码工具**；9/6 实测 Hermes 经 `--provider zhipu` + Coding Plan 端点（open.bigmodel.cn/api/coding/paas/v4）直调 glm-5.3/glm-5.3-flash 未被拒（Model Router 实验），细节见 myps-operations references/model-switching.md。**2026-09-18 用户确认：MyPS 的 GLM key 就是 Coding Plan 套餐 key（未单独购买 API）——MyPS 与 Codex 共享同一 Lite 积分池**。⚠️ 归因纪律（9/18 教训）：答「MyPS 走什么通道/谁付账」前以此条为准，勿凭印象说「zai 直连独立计费/两条账」——曾被用户当场纠正。消耗结构：MyPS 主用 flash 低系数档且 cron 多在非高峰，池子消耗温和；Codex 用 GLM-5.3 重会话才是大头。计费：非高峰（14-18 点外，含周末全天）50%、深夜 23:00-09:00 flash 无限。
- **Agnes Code**（⚠️ 用户 2026-08-21 明确纠正：工具名叫 Agnes Code，**没有「Claude Code」这个叫法**，记录/对话一律用 Agnes Code）。多模态大模型可生成图，每日赠送 1200 点额度。PPT/文档类轻任务消耗极小（8/20 实测：弘途公司介绍 PPT 全程完成无压力）——与 某第三方AI助手「PPT 耗点数极快」形成对比，做演示类任务优先推荐。自带 Coding 界面，直接用即可；曾尝试经 CC Switch 把 Agnes API 接入 Codex 客户端未成功（8/20），不必强求接入。
- **Agnes AI API（中国站）**（2026-09-06 接入验证）：OpenAI 兼容，Base URL `https://api.agnes-ai.cn/v1`，key 存 ~/.hermes/.env 的 `AGNES_API_KEY`（**API key ≠ 客户端 1200 点/天**，需控制台单独创建）。模型：`agnes-2.5-flash`/`agnes-2.5-pro`/`pro-beta`（文本）、`agnes-image-2.x-flash`（生图）；**agnes-2.5-flash 原生多模态能看图**（四色象限图实测通过，image_tokens 计费同 DeepSeek vision）+ prompt 缓存支持。当前促销期文本+图像全免费（结束时间未公告，不作底座依赖）。9/6 起 MyPS 的 auxiliary.vision 切到 agnes-2.5-flash（免费看图）。⚠️ 忆旧查询场景易直接断言"没找到"（评测必考题翻车），做主模型需强化规则。可直接用于 MyPS 评测/备选后端，详见 tools/llm-cost-analysis。
- **三模型分工（Model Router，2026-09-06 定案）**：日常碎片/记录 = DeepSeek v4-flash；技术活（编程讨论/测试分析/LUMA 架构类）= GLM-5.3 系列（Coding Plan 直连：hermes --provider zhipu -m glm-5.3-flash，key 在 .env GLM_API_KEY+GLM_BASE_URL）；看图/生图 = Agnes（auxiliary.vision 已切）。A/B 评测依据见 tools/model-selection-eval skill。
- **某第三方AI助手 积分自动签到（2026-09-20 起，hermes 主机托管）**：github.com/88lin/workbuddy-auto-signin（491星/MIT/纯标准库单文件 signin.py，读本地凭据打 copilot.tencent.com 官方签到接口，幂等，含成长中心领取+断签补卡）。部署：仓库在 hermes 主机 `~/workbuddy-auto-signin`，CodeBuddy CLI v2.155.0 装在 `~/.npm-global`（npm 全局 EACCES 的绕法：`npm config set prefix ~/.npm-global`）。**无头 Linux 登录 CodeBuddy CLI 的方法**（TUI REPL 在 script/PTY 包装下键盘交互不可靠）：`codebuddy --serve --host 0.0.0.0 --port 8765 --auth none` 起 Web UI，用户从同网段浏览器开 http://<局域网IP>:8765 输 /login 选 Chinese Site 完成认证，登录完关服务。完整部署状态/运维 SOP（登录失效恢复、cron 结构、坑清单、验收监控）见 `references/workbuddy-signin-托管.md`（**权威源**——原独立 skill workbuddy-signin-ops 已于 2026-09-21 并入本 reference，勿再双处维护）。选型背景：办公室机器每天关机，工作日靠上班时段轮询可签但周末断档 → 用户拍板 MyPS 主机 24h 托管。**当日部署完成并实测通过**（CLI 登录 → signin.py status 返回连签 5 天/活动累计 500 分，与桌面端同账号）。注意双池积分：活动面板积分（500）≠ 账户消费型余额（桌面端显示 2888.25，接口未找到，余额看桌面端）。⚠️ 签到 API 逆向自客户端，腾讯更新可能失效（作者跟进修复）
- **某第三方AI助手**：另有资料库功能（可连 IMA 资料直接分析），PPT/长任务耗点数极快，外网 Skill 慎用（见 knowledge/CodeX.md 教训）。⚠️ **微信 iLink bot 互斥（9/6 事件）**：某第三方AI助手 连接微信（iLink bot 扫码）会顶掉 MyPS 的微信会话——两者共用同一微信号时单 bot 在线，谁后连谁生效。用户连过 某第三方AI助手 微信后 MyPS 失联；修复用 myps-operations 的 wx-fix 一键脚本。排查用户失联时先问"最近连过 某第三方AI助手/其他扫码服务吗"。**某第三方AI助手 产出资产（均发布 GoodVFX GitHub）**：life-designer（2026-07 人生设计对话 skill）、strengths-finder（2026-07 盖洛普优势发现 skill）、pdf2md（2026-09-08 扫描 PDF→MD 管线，Python/MIT）、ip-coaching-interview（2026-09-08 教练式 IP 访谈技能包，源自 1.5h IP 访谈提炼）——完整清单见 data/knowledge/用户-GitHub仓库资产.md + pdf2md-扫描版PDF转MD.md
- 旧配置：CC Switch 中转连接用户自己的 API（赠送少量额度）——已弃用。

⚠️ 工具连接方式经常变。以 `data/knowledge/` 下对应主题文件（CodeX.md 等）的最新记录为准，本 Skill 只记排查模式，不记死配置。

## 经典坑：中转（Relay）赠送额度耗尽

**症状**：客户端报「调用频繁」/ rate limited / 连接受限，但官方后台（GLM / coding plan 用量页）**查不到任何使用量**。

**根因**：报错来自中转服务而非官方——中转连接的是用户自己的 API，之前赠送的少量额度耗尽后即限流；官方账上没有这笔消耗，所以后台无记录。

**诊断路径**（2026-08-18/19 实战验证）：
1. 先查是否走了中转（CC Switch 等）→ 查中转账户赠送额度余额
2. 官方后台无用量 ≠ 无消耗——额度可能消耗在中转侧
3. 别急着下「工具误报/限流」结论，先排除中转额度因素
4. 修复方向：换官方直连（本例 GLM 原生支持 Codex → 直连 Coding Plan），绕开中转层

## 定价/账单/成本分析 → 归口 tools/llm-cost-analysis

用户发定价页/套餐链接要求解读、导出 API 账单 CSV 要求归因、问「哪个模型性价比高/更适合某场景」时——完整套路（定价页四要素解读 + 单次会话体感换算 + 账单归因流程 + 多模型 A/B 评测 + 会话膨胀税 + 归档约定）见 **tools/llm-cost-analysis**；CSV 字段语义（cost/amount 表、type 四类、price 反推时段档）与日志诊断命令见本 skill 的 `references/api-cost-analysis.md`。工具链专属残留约定：订阅落定后在 knowledge/ 对应工具文件追加订阅记录 + diary/events 双写。



## 处理约定

- 工具配置/接入方式变更 → 更新 knowledge/ 对应工具文件 + 当日 diary/events 双写 + 建待办（接入动作），用户确认完成后标记
- 故障根因事后确认 → 在 knowledge/ 对应文件追加「根因确认」条目，保留原推测条目不删（追加而非覆盖）
- 具体案例细节 → `data/knowledge/CodeX.md` 等（用户数据，有 git 备份）

## Claude Code 溯源（哪台机器、何时做过什么）

用户问「某次 Claude Code 操作在哪台机器做的 / 当时有没有记录」→ 属**跨机器会话取证**类，类级方法归口 **tools/lan-file-retrieval**，本 skill 不再重复维护其细节：生成机器判定证据链（`~/.claude.json` 的 firstStartTime 首装时间、`~/.claude/projects/` jsonl 会话流水、git `Co-Authored-By` 痕迹、CRLF 换行符判定、文件 mtime 只证拷贝时刻不证创作地）+ Claude Code 记录结构与完整溯源实录，均在其 SKILL.md 与 `references/claude-code-records.md`。

⚠️ 唯一要点：会话记录只在**运行过它的那台机器**本地——本机查不到就经 lan-file-retrieval 远程读共享（SMB/U 盘镜像），别在本机空翻。

