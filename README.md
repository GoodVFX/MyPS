---
title: README.md
type: project-readme
description: MyPS 个人 AI 助理系统——项目总览、目录结构、快速上手。
version: 4.0
created: 2026-05-31
updated: 2026-10-02
---

# MyPS — 你的个人 AI 助理

MyPS（My Personal Secretary）是一个运行在 Hermes Agent 之上的个人 AI 助理系统。

它的核心理念很简单：**你只管说，它负责记、管、提、关怀。**

---

## 这个系统能做什么

- **记事**：你随口说的碎碎念，它即时分类（日记/灵感/待办/好句/记账/事件/知识），带时间戳存档，一句确认
- **待办**：三类事务独立管理——长待办（项目）、常规待办（琐碎）、定时待办（有截止时间）
- **提醒**：到时间主动找你，硬期限多重提醒
- **关怀**：每天早晚各一次主动推送——早上日程规划，晚上今日总结 + 情绪教练
- **学习辅助**：你口述的知识碎片按主题积累，到量了主动提议帮你整理
- **长项目陪伴**：跨周/跨月的长期项目持续跟踪，记住愿景，温和推动进展
- **自愈运行**：Gateway 进程挂了自动拉起，断电重启后自动恢复（见 `docs/gateway-watchdog.md`）

---

## v4.0 更新说明

v4.0 聚焦**记忆生命周期**与**自愈能力**的升级。相比 v3.0，核心变化：

| 变化 | v3.0 | v4.0 |
|------|------|------|
| 记忆维护 | 水位满了提醒用户手动清理 | **每晚自主 consolidation**——水位 ≥86% 当晚自动整理（快照回滚锚点 + 三个月判据 + 事实无损硬约束），用户只看结果 |
| 记忆固化 | 惊奇度扫描提议写入 | + **固化提案（reflect 闭环）**——每晚自问「新会话的我该记住什么」，用户回复「固化」即写入，三个月判据准入 |
| 成长回放 | 无 | **journey 月度机制**——每月 1 日自动生成上月成长档案（技能沉淀/记忆演化/里程碑/待办完成/本月叙事），水位趋势日志联动 |
| 技能体系 | 11 个 SKILL.md | 16 个——新增豆包 TTS 接入、SSL 证书续期、LLM 成本分析、模型 A/B 选型评测、AI 编码工具链 |
| 微信自愈 | Gateway 进程 watchdog | + **wx-fix 一键恢复脚本**——微信被其他客户端顶掉后，扫码即自动恢复（含凭据更新与 gateway 重启全流程） |
| 辅助文档 | gateway-watchdog.md | + `docs/memory-consolidation-journey.md`（记忆 consolidation 与成长回放机制完整手册） |

---

## v3.0 更新说明

v3.0 是 MyPS 经过两个多月真实使用后的运行级升级。相比 v2.0（功能完整实现），核心变化：

| 变化 | v2.0 | v3.0 |
|------|------|------|
| 技能体系 | 6 个核心 Skill | 6 核心 + 3 扩展 + 2 类级协议（见目录结构） |
| 碎片捕获 | 8 类分类 | + 批量任务组特殊处理 + 项目设计决策归档 + 命名约定同步 + 硬件规格实测优先 |
| 晚间总结 | 完整分析流程 | + 月度总结扩展 + 重跑检测 + 锻炼完成检测 + 数据完整性检查 |
| 情绪教练 | 分析流程 | + 连续静默日处理 + 零交互日区分 + 写入验证 |
| 数据备份 | 框架建议 | 独立 data-backup Skill——git 增量备份到 GitHub 私有仓库，含备份积压检测与恢复流程 |
| 长项目陪伴 | 无 | 新增 project-coach Skill——愿景对齐、进度推动、竞品情报跟踪 |
| 系统运维 | 无 | 新增 myps-operations Skill——Cron/Skill 对应关系、Gateway 失效排查、停机恢复、watchdog 守护 |
| **进程自愈** | 无 | **Gateway watchdog 守护**——进程挂了 1 分钟内自动拉起，断电重启自动恢复（详见 `docs/gateway-watchdog.md`） |

---

## 目录结构

```
MyPS/
├── README.md                  ← 你正在看的文件
├── INSTALL.md                 ← 安装步骤指导（从零开始）
├── docs/
│   ├── gateway-watchdog.md    ← Gateway 进程自愈守护方案（v3.0 辅助文档）
│   └── memory-consolidation-journey.md ← 记忆整理与成长回放机制（v4.0 辅助文档）
│
├── SOUL.md                    ← AI 的人格——它是什么样的搭档、怎么和你说话
├── USER.md                    ← 你的档案——你是谁、怎么沟通、什么能自动做什么不行
├── MEMORY.md                  ← 记忆索引——指向 memory/ 下详细文件的压缩索引
├── AGENTS.md                  ← 工作空间说明书——目录长什么样、数据什么格式、操作规则
│
├── memory/                    ← 详细记忆存储
│   ├── preferences.md         ← 关于你的偏好和习惯
│   ├── patterns.md            ← 关于你的行为规律
│   └── mood-trends.md         ← 你的情绪趋势追踪
│
├── data/                      ← 你的个人数据
│   ├── todos.json             ← 三类待办数据
│   ├── projects/              ← 大项目文件（每个项目一个 .md）
│   ├── diary/                 ← 日记（按日期）
│   ├── ideas/                 ← 灵感库
│   ├── quotes/                ← 好言好句
│   ├── expenses/              ← 记账
│   ├── events/                ← 事件记录
│   ├── knowledge/             ← 知识碎片（按主题积累）
│   ├── inbox/                 ← 未分类碎片
│   └── archive/               ← 已完成/过期的归档
│
├── skills/                    ← 技能目录（按需加载）
│   │
│   ├── 核心技能（6 个，日常运行）
│   ├── fragment-catcher/      ← 碎片捕获器——你说话它分类
│   ├── task-manager/          ← 待办管理器——三类待办增删改查
│   ├── reminder-engine/       ← 提醒引擎——到点找你
│   ├── daily-briefing/        ← 早间简报——每天 8:30 日程规划
│   ├── daily-review/          ← 晚间总结——每天 22:00 今日回顾
│   ├── emotion-coach/         ← 情绪教练——情绪评价和趋势记录
│   │
│   ├── 扩展技能（3 个，v3.0 新增）
│   ├── data-backup/           ← 数据备份——git 增量备份到 GitHub 私有仓库
│   ├── project-coach/         ← 长项目陪伴——愿景对齐、进度推动
│   └── myps-operations/       ← 系统运维——Cron/Skill 对应、故障排查、恢复、wx-fix 微信自愈
│   │
│   ├── 扩展技能（5 个，v4.0 新增）
│   ├── doubao-tts/            ← 豆包语音合成接入——鉴权、音色选型、流解析
│   ├── ssl-cert-renewal/      ← SSL 证书续期——到期盯梢、部署验证
│   ├── tools/llm-cost-analysis/       ← LLM 成本分析与模型选型
│   ├── tools/model-selection-eval/    ← 模型 A/B 选型评测
│   └── tools/ai-coding-tools/         ← AI 编码工具链管理
│   │
│   └── 类级协议（2 个，场景化行为定义）
│       ├── interaction/interaction-protocols/   ← 场景化交互协议（连接测试、工具学习等）
│       └── research/project-research/           ← 外部项目调研与借鉴分析
│
├── cron/                      ← 定时任务配置
└── sessions/                  ← 会话历史（由 Hermes SessionDB 管理，不手动修改）
```

---

## 快速上手

1. 确认已安装 Hermes Agent（详见 [INSTALL.md](INSTALL.md)）
2. 将本目录下的文件复制到 `~/.hermes/` 目录
3. 编辑 `USER.md`，填入你的个人信息（替换 `[占位符]`）
4. 启动 Hermes，开始使用

---

## 设计思路

MyPS 的定位是**「外脑记事本」**，不是知识管理系统。核心交互是：

```
你口述碎碎念 → AI 即时分类存档回复 → 到点主动提醒关怀
```

系统的记忆分为四层：

| 层级 | 存什么 | 存在哪 |
|------|--------|--------|
| 身份 | 你是谁、怎么沟通 | SOUL.md + USER.md |
| 工作 | 待办、每日记录 | todos.json + data/ |
| 洞察 | 模式、偏好、情绪趋势 | MEMORY.md 索引 → memory/ |
| 隐记忆 | 所有历史对话 | SessionDB（Hermes 原生） |

技能按需加载：核心 6 个各司其职，扩展 8 个覆盖备份/项目/运维/语音/证书/成本分析/模型评测/工具链，类级 2 个定义特殊场景行为。

完整设计方案见项目根目录下的 `sheji.md`。

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
