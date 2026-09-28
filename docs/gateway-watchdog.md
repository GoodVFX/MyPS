---
title: gateway-watchdog.md
type: auxiliary-doc
description: MyPS Gateway 进程自愈守护方案——watchdog 脚本原理、部署、验证与排障。
version: 1.0
created: 2026-08-17
applies-to: v3.0
---

# Gateway 进程自愈守护（Watchdog）

> 本文件是 MyPS v3.0 的辅助文档，单独说明 Gateway 进程自动重启的完整方案。
> 它不参与 MyPS 主框架（SOUL/AGENTS/Skills），属于**运行层保障**。

---

## 为什么需要它

MyPS 的 Gateway 是常驻进程（`hermes gateway run`），负责：

- 接收和回复用户消息
- 执行 Cron 定时任务（早间简报、晚间总结、提醒）

**没有守护时**：Gateway 一旦退出（崩溃、被杀、断电重启），系统就静默停摆——消息没人回、提醒不推送，而且**没有自动恢复机制**。

对于「机器常年开机、无人值守」的部署场景（如 Linux Deploy 容器、树莓派、NAS），这是必须解决的可靠性问题。

---

## 环境约束（为什么不用 systemd）

| 方案 | 本环境可用？ | 原因 |
|------|------------|------|
| systemd service | ❌ | 容器内 PID 1 不是 systemd，`systemctl` 全线不可用 |
| supervisor | ❌ | 曾配置 `/etc/supervisor/conf.d/`，启动即失败（exit 1），弃用 |
| crond + @reboot | ❌ | 容器内 crond 未运行 |
| **自建 watchdog 脚本** | ✅ | 每 30s 轮询检测 + 自动拉起，挂在 rc.local 开机自启 |

---

## 方案原理

```
┌─────────────────────────────────────────────┐
│  rc.local（开机钩子，容器每次启动执行）        │
│  1. 拉起 gateway                             │
│  2. 拉起 watchdog（防重复：已存在则跳过）      │
└──────────────┬──────────────────────────────┘
               │
    ┌──────────▼──────────┐
    │   watchdog 脚本      │  ← 每 30 秒轮询
    │  (gateway-watchdog)  │
    └──────────┬──────────┘
               │ 检测 gateway 主进程是否存活
               │（精确匹配 python 进程，连续 2 次缺失才判定）
    ┌──────────▼──────────┐
    │  检测到 → 自动拉起    │  ← nohup 后台启动新 gateway
    │  存活   → 继续等待    │
    └─────────────────────┘
```

**核心机制**：

1. **每 30 秒**检查一次 gateway 主进程（精确匹配 `venv/bin/python.*gateway run`）
2. **连续 2 次检测不到**（约 1 分钟）才触发拉起——避免 gateway 优雅关闭期间的误判
3. 拉起命令用 `nohup ... &` 后台运行，并写日志
4. watchdog 自身由 rc.local 开机拉起，**与 gateway 完全独立**（PPID=1）

---

## 关键设计：watchdog 必须独立于 gateway

这是本方案**最重要的一条教训**。

**❌ 错误形态**：watchdog 作为 gateway 的子进程/同会话进程启动

```
gateway ── 派生 ──> watchdog   ← 错误！
gateway 退出时，watchdog 被连带杀死
watchdog 死了，没人拉 gateway → 守护链断裂
```

**✅ 正确形态**：watchdog 由 rc.local 独立拉起（PPID=1）

```
rc.local ── 拉起 ──> watchdog（PPID=1，独立进程组）
rc.local ── 拉起 ──> gateway
watchdog 检测 gateway → 挂了就拉起，自己不会被连带杀
```

> 实战教训（2026-08-17）：手动在终端后台启动 watchdog 时，它是 gateway 会话的子进程。gateway 优雅关闭时**连带杀死了 watchdog**，导致守护失效。改用 rc.local 独立拉起后，击杀 gateway 演练中 watchdog 全程存活并成功自动拉起新 gateway。

---

## 部署步骤

### 1. 脚本文件

保存为 `~/.hermes/scripts/gateway-watchdog.sh`：

```bash
#!/bin/bash
# MyPS Gateway 自愈守护——每 30s 检测，连续 2 次缺失则自动拉起
# 由 rc.local 独立拉起（勿作为 gateway 子进程运行）

WATCHDOG_LOG=~/hermes-watchdog.log
GATEWAY_PIDFILE=~/.hermes/gateway.pid

check_gateway() {
  # 精确匹配 python 主进程，避免误匹配 bash 包装/日志文本
  pgrep -f "venv/bin/python.*gateway run" > /dev/null 2>&1
}

miss_count=0
while true; do
  if check_gateway; then
    miss_count=0
  else
    miss_count=$((miss_count + 1))
    if [ $miss_count -ge 2 ]; then
      echo "$(date '+%F %T') gateway 缺失，自动拉起" >> "$WATCHDOG_LOG"
      source ~/venv/bin/activate
      nohup hermes gateway run >> ~/hermes-gateway.log 2>&1 &
      miss_count=0
    fi
  fi
  sleep 30
done
```

> 注：路径按实际环境调整（venv 路径、hermes 可执行文件位置）。

### 2. 挂载开机自启

编辑 `/etc/rc.local`，在 gateway 启动行之后追加：

```bash
# MyPS gateway 守护（防重复：已运行则跳过）
pgrep -f "gateway-watchdog.sh" > /dev/null || nohup bash ~/.hermes/scripts/gateway-watchdog.sh &
```

### 3. 手动启动（立即生效）

```bash
nohup bash ~/.hermes/scripts/gateway-watchdog.sh &
```

验证：

```bash
pgrep -af gateway-watchdog.sh    # 应看到 watchdog 进程
ps -o pid,ppid,cmd -p $(pgrep -f "gateway run" | head -1)
# watchdog 的 PPID 应为 1（独立），gateway 的 PPID 应为 1 或 watchdog
```

---

## 验证：真实演练（必做）

部署后**必须做一次真实击杀演练**，不能只看脚本逻辑就宣布成功。

**流程**：

1. 击杀 gateway 主进程（让其优雅关闭）
2. 等待 3 分钟（watchdog 检测 2 次缺失约 1 分钟 + 拉起 + 通道重连）
3. 从微信/企微发一条测试消息（如「在吗」）
4. 收到回复 = 链路完整跑通

**验证关键点**：

| 检查项 | 证据 |
|--------|------|
| watchdog 未被连带杀死 | `ps -p <watchdog_pid>` 仍存活，PPID=1 |
| 新 gateway 被拉起 | 新 PID ≠ 旧 PID，启动时间在击杀后 ~1 分钟 |
| 新 gateway 归属正确 | `ps -o ppid -p <新PID>` = watchdog PID（或 1） |
| 通道恢复 | `gateway_state.json` 中 weixin/wecom 均为 connected |

**⚠️ 验证陷阱**：

- **进程起来了 ≠ 通道通了**：gateway 拉起后平台通道是**异步重连**的——微信约 10 秒连上，企业微信可能重连失败数次、耗时约 3 分钟。用户报「没反应」时，先查 `gateway_state.json` 和 gateway.log，确认是「没起来」还是「通道没通」
- **回复投递可能延迟**：gateway 重启后第一波回复可能因投递未确认被排队补发，等 1-2 分钟再看
- **不要用 `pgrep -f "hermes gateway run"` 做宽泛检测**：gateway 优雅关闭期间进程仍在（等待当前会话结束），且 bash 包装进程也含该字符串 → 会误判存活 → 不拉起。必须精确匹配 python 主进程路径 + 连续 2 次缺失

---

## 排查清单

| 现象 | 排查路径 |
|------|---------|
| 用户发消息无回复 | `ps aux \| grep "gateway run"` → 无进程 = gateway 挂了，看 watchdog 为何没拉 |
| watchdog 在但没拉起 | 检查日志 `~/hermes-watchdog.log`；确认检测匹配条件（pgrep 模式是否精确） |
| gateway 起来了但用户没反应 | 查 `~/.hermes/gateway_state.json` 的 platforms 状态；查 gateway.log 重连记录 |
| 开机后 gateway 没自动起 | 检查 rc.local 是否执行、watchdog 是否被拉起（PPID=1） |
| 重复 watchdog 实例 | `pgrep -f gateway-watchdog.sh` 排除 `bash -c` 包装行再数 |

---

## 恢复后的检查（gateway 重启后）

- ✅ 微信/企微连接自动恢复（异步，约 10s-3min）
- ✅ Cron 调度器重新开始计时
- ❌ **已错过的 Cron 不会补跑**（超过 2 小时 grace 直接跳到下次）——重要推送用 `cronjob action='run'` 手动补
- ❌ 停机期间用户发的消息无法补收（微信长连接断开不补投离线消息）——提醒用户补发重要内容

---

## 局限

- watchdog 只能拉起 gateway 进程，**不能解决平台侧限速**（微信 iLink 主动推送限流）
- 检测间隔 30s + 连续 2 次缺失 ≈ 最长 1 分钟恢复窗口，期间消息不可达
- 如果 gateway 因配置错误反复崩溃，watchdog 会反复拉起——需结合日志定位根因，而不是只靠守护兜底

---

*MyPS v3.0 辅助文档 · 2026-08-17*
