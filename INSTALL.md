---
title: INSTALL.md
type: installation-guide
description: MyPS 在纯净 Hermes Agent 环境下的完整安装步骤指导。
version: 4.0
created: 2026-05-31
updated: 2026-10-02
---

# 安装指导

本文件指导你在一台**全新安装了 Hermes Agent** 的环境中，从零部署 MyPS 个人助理系统。

---

## 前提条件

在开始之前，确保以下条件已满足：

| 条件 | 要求 | 验证方法 |
|------|------|---------|
| Hermes Agent | 已安装并可运行 | 终端执行 `hermes --version`，能看到版本号 |
| Python | 3.10 或更高 | `python --version` |
| API 密钥 | 已配置 Hermes 使用的模型 API 密钥 | 启动 Hermes 能正常对话 |
| 工作目录 | 知道 Hermes 的 HOME 目录位置（通常是 `~/.hermes/`） | `echo $HERMES_HOME` 或查看 Hermes 配置 |

> **说明**：本系统不依赖任何额外的包管理器、编译步骤或数据库。所有数据都是纯文本（Markdown + JSON）。
> 如果你还没安装 Hermes，请先前往 https://github.com/NousResearch/hermes-agent 完成安装。

---

## 第一步：确认 Hermes 环境

打开终端，执行以下命令确认 Hermes 运行正常：

```bash
# 查看 Hermes 版本
hermes --version

# 查看 HOME 目录位置
hermes config home
```

记下 HOME 目录的路径。以下步骤假设 HOME 目录为 `~/.hermes/`，如果你的路径不同，请替换。

---

## 第二步：备份已有数据（如果有的话）

如果你的 `~/.hermes/` 目录下已经有文件（比如之前用过 Hermes），先做个备份：

```bash
# 备份整个 Hermes HOME 目录
cp -r ~/.hermes ~/.hermes.backup.$(date +%Y%m%d)
```

> 如果是全新安装的 Hermes，跳过此步。

---

## 第三步：复制 MyPS 系统文件

将 MyPS 目录下的文件复制到 Hermes HOME 目录。

```bash
# 进入 MyPS 源文件目录（替换为你实际的 MyPS 路径）
cd /path/to/MyPS

# 复制核心文件到 Hermes HOME
cp SOUL.md   ~/.hermes/SOUL.md
cp USER.md   ~/.hermes/USER.md
cp MEMORY.md ~/.hermes/MEMORY.md
cp AGENTS.md ~/.hermes/AGENTS.md

# 复制记忆模板目录
cp -r memory/  ~/.hermes/memory/

# 复制数据目录（会自动创建子目录）
cp -r data/    ~/.hermes/data/

# 复制技能目录
cp -r skills/  ~/.hermes/skills/

# 复制 Cron 配置目录
cp -r cron/    ~/.hermes/cron/
```

复制完成后，Hermes HOME 目录应该长这样：

```
~/.hermes/
├── SOUL.md
├── USER.md
├── MEMORY.md
├── AGENTS.md
├── memory/
│   ├── preferences.md
│   ├── patterns.md
│   └── mood-trends.md
├── data/
│   ├── todos.json
│   ├── projects/
│   ├── diary/
│   ├── ideas/
│   ├── quotes/
│   ├── expenses/
│   ├── events/
│   ├── knowledge/
│   ├── inbox/
│   └── archive/
├── skills/
│   ├── fragment-catcher/SKILL.md
│   ├── task-manager/SKILL.md
│   ├── reminder-engine/SKILL.md
│   ├── daily-briefing/SKILL.md
│   ├── daily-review/SKILL.md
│   └── emotion-coach/SKILL.md
├── cron/
└── sessions/          ← Hermes 自动管理
```

**验证**：

```bash
# 检查核心文件是否存在
ls ~/.hermes/SOUL.md ~/.hermes/USER.md ~/.hermes/MEMORY.md ~/.hermes/AGENTS.md

# 检查记忆文件是否存在
ls ~/.hermes/memory/

# 检查数据目录是否存在
ls ~/.hermes/data/

# 检查技能文件是否存在
ls ~/.hermes/skills/*/
```

所有命令都应输出对应的文件路径，没有报错。

---

## 第四步：配置你的个人信息

打开 `~/.hermes/USER.md`，将占位符替换为你的实际信息：

```bash
# 用你喜欢的编辑器打开
nano ~/.hermes/USER.md
# 或
code ~/.hermes/USER.md
```

**必须填写的字段**：

| 字段 | 当前值 | 替换为 |
|------|--------|--------|
| 姓名 | `[你的名字]` | 你的真实姓名或昵称 |
| 职业 | `[你的职业/职位]` | 你的实际职业 |
| 所在地 | `[城市/地区]` | 你所在的城市 |
| 时区 | `[如 UTC+8]` | 你的时区（中国填 `UTC+8`） |
| 当前角色 | `[角色 1]` 等 | 你当前的身份和职责 |

**可选填写**：

- 关键人物表（如果你经常提到某些人，填入可帮助 AI 理解上下文）
- 核心术语表（你常用的行话、缩写）

> 提醒偏好和碎片处理规则已经有合理的默认值，通常不需要修改。如果需要调整，直接编辑对应区块即可。

---

## 第五步：启动 Hermes 并测试

```bash
# 启动 Hermes
hermes
```

启动后，尝试以下测试：

### 测试 1：碎片分类

输入一句碎碎念：

```
今天看了篇讲 RAG 的文章，检索增强生成就是把外部知识检索出来喂给大模型
```

**期望结果**：AI 回复类似「📚 知识 → RAG，已记录」。

### 测试 2：待办创建

```
明天下午三点前要给张总发方案
```

**期望结果**：AI 回复类似「📋 定期待办，截止明天 15:00，提醒已设」。

### 测试 3：待办查询

```
有什么事要做？
```

**期望结果**：AI 展示你的待办列表（刚创建的那条应该在里面）。

如果三个测试都通过，说明系统基本工作正常。

---

## 第六步：配置 Cron 定时任务

MyPS 依赖两个 Cron 任务来实现早晚自动推送。

### 6.1 早间简报（每天 8:30）

在 Hermes 对话中输入：

```
创建一个 Cron 任务，每天早上 8:30 执行 daily-briefing 技能，
推送当天的日程规划给我。
```

Hermes 会自动创建定时任务。确认它创建了：
- 触发时间：`30 8 * * *`（每天 8:30）
- 调用的 Skill：daily-briefing
- 推送方式：origin（发送到创建时的同一平台）

### 6.2 晚间总结（每天 22:00）

```
创建一个 Cron 任务，每天晚上 22:00 执行 daily-review 技能，
推送当天的总结和情绪教练评价给我。
```

确认：
- 触发时间：`0 22 * * *`（每天 22:00）
- 调用的 Skill：daily-review
- 推送方式：origin

**验证**：

```bash
# 查看 Hermes 的 Cron 任务列表
hermes cron list
```

应该能看到两个定时任务。

---

## 第七步：多平台接入（可选）

如果你想在手机上使用（WhatsApp / Telegram），需要配置 Hermes Gateway。

### WhatsApp

```bash
# 配置 WhatsApp Gateway
hermes gateway setup whatsapp
```

按照提示扫码绑定你的 WhatsApp 账号。

### Telegram

```bash
# 配置 Telegram Gateway
hermes gateway setup telegram
```

按照提示输入 Bot Token（需要先通过 @BotFather 创建一个 Telegram Bot）。

配置完成后，在手机上发一条碎碎念测试是否能正常接收和回复。

---

## 第八步：确认一切正常

安装完成。做一次全面检查：

| 检查项 | 方法 | 期望结果 |
|--------|------|---------|
| AI 人格 | 对话几句，观察语气 | 不像客服，像搭档。不说过度客气的话 |
| 碎片分类 | 发不同类型的碎碎念 | 8 类都能正确分类 |
| 待办管理 | 创建各类待办，查询 | 三类待办独立管理，全局视图正确 |
| 提醒 | 创建定时待办 | 自动设置 Cron 提醒 |
| 记忆存储 | 查看 data/ 目录 | 碎片按分类存入对应目录 |
| 早间简报 | 等 8:30 或手动触发 | 推送日程规划 |
| 晚间总结 | 等 22:00 或手动触发 | 推送今日总结 + 情绪评价 |

---

## 实战调优：Cron 推送的陷阱与解决方案

> 以下经验来自实际部署，帮你避开常见坑。

### 微信平台推送

如果在微信上使用 Hermes，Cron 推送默认的 `deliver: origin` 可能无法正确路由到你的会话。

**解决方案**：创建 Cron 时显式指定微信 chat ID：

```bash
# 先获取你的微信 chat ID
hermes channels list

# 创建 Cron 时指定目标
hermes cron create \
  --name "daily-briefing" \
  --schedule "30 8 * * *" \
  --skill daily-briefing \
  --deliver "weixin:你的微信chatID" \
  --workdir "$HOME/.hermes"
```

### 必须设置 workdir

MyPS 的技能在读取数据文件时使用相对路径（如 `data/todos.json`），相对于 `~/.hermes/` 解析。如果 Cron 任务未设置 workdir，数据文件会解析到错误位置，输出为空且被静默抑制——你完全收不到推送，但系统显示运行正常。

**务必**：每个 Cron 任务都要设置 `workdir='/home/你的用户名/.hermes'`。

### 推送延迟

Cron 调度器存在约 4 分钟的轮询延迟。如果你的 Cron 需要精确到分钟（比如 8:30 准时推送），可将触发时间提前 5 分钟。

### 静默写失败

晚间总结（daily-review）在写入情绪趋势文件（mood-trends.md）时，可能因 patch 路径问题而静默失败——系统无报错，但数据未落盘。v2.0 已内置写入验证机制，写入后自动读取确认。

---

## 数据备份建议

MyPS 的所有数据都是文本文件（Markdown + JSON），推荐用 GitHub 私有仓库做定时备份：

1. 在 GitHub 创建一个**私有仓库**
2. 在 `~/.hermes/` 目录初始化 git：
   ```bash
   cd ~/.hermes
   git init
   git remote add origin git@github.com:你的用户名/你的备份仓库.git
   ```
3. 创建 `.gitignore` 排除不需要备份的目录：
   ```
   sessions/
   cron/output/
   ```
4. 设置 Cron 定时备份：
   ```bash
   # 每天凌晨自动 commit + push
   0 3 * * * cd ~/.hermes && git add -A && git commit -m "每日备份 $(date +%Y-%m-%d)" && git push
   ```

**恢复方法**：新机器上装好 Hermes Agent → clone 私有仓库到 `~/.hermes/` → 直接恢复全部数据和技能。

---

## 常见问题

### Q: 启动 Hermes 后它不知道我是谁？

确保 USER.md 已正确填写，且位于 Hermes HOME 目录（`~/.hermes/USER.md`）。Hermes 启动时会自动加载。

### Q: 碎片分类不准确？

分类规则在 `skills/fragment-catcher/SKILL.md` 中定义。你可以直接编辑这个文件来调整分类逻辑，或者在使用中纠正 AI，它会通过 Skill 自进化机制逐渐学习你的偏好。

### Q: Cron 任务没触发？

检查 Hermes 是否持续运行。Cron 任务需要 Hermes 进程在线才能触发。可以用 `hermes cron list` 查看任务状态。

### Q: 我想调整提醒时间？

编辑 `USER.md` 中的「提醒偏好」区块，修改「可打扰时间」「静默期」等设置。修改后下次会话生效。

---

## 致谢

本系统的设计理念受到了 **Memory Work**（个人 AI 搭档知识管理系统）的深刻启发。

- **项目地址**：https://github.com/yiliqi78/memory-work
- **作者**：[@yiliqi78](https://github.com/yiliqi78)

Memory Work 由 [@yiliqi78](https://github.com/yiliqi78) 创建，首创了分层记忆架构、惊奇度驱动写入、区域代理治理等核心方法论，为本系统提供了宝贵的思路基础。特别是在记忆的生命周期管理、惊喜驱动的信息过滤、以及 AI 人格的精细化定义等方面，Memory Work 的探索具有开创性的参考价值。

本系统在 Memory Work 的理念之上进行了全新设计和实现，聚焦于「外脑记事本」场景——面向碎片化日常记事、三类待办管理、主动关怀提醒、情绪教练、知识碎片积累的需求。所有文件均为全新编写，未复制 Memory Work 的任何原始文本。

特此向 Memory Work 项目及其作者 [@yiliqi78](https://github.com/yiliqi78) 致以诚挚的敬意和感谢。

---

*MyPS v4.0 · 2026-10-02*
