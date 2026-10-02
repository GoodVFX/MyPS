#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信一键恢复脚本（MyPS / Hermes iLink Bot）
=============================================
用途：微信通道被其他客户端顶掉（Session expired）后，SSH 进容器跑本脚本，
      按提示用手机微信扫码，自动完成：取新凭据 → 更新 .env → 重启 gateway → 验证。

用法：
    python3 wx_fix.py
    （以运行 Hermes 的用户身份跑即可；root 跑也可以，脚本内部会切换文件属主）

可配置环境变量（默认值适配标准单用户安装）：
    HERMES_HOME  Hermes 配置目录（默认 ~/.hermes；★ 必须是 .hermes，账号目录拼接不含 .hermes）
    HERMES_USER  Hermes 运行用户（默认当前用户）
    HERMES_VENV  Hermes venv 路径（默认 ~/hermes-venv）

流程：检查状态 → 拉二维码（终端显示 + 存 PNG）→ 等你扫码 → 自动安装凭据
      → 重启 gateway（watchdog 自动拉起）→ 验证 sync 游标 → 报告结果
"""
import asyncio
import json
import os
import pwd
import shutil
import stat
import subprocess
import sys
import time

import aiohttp

HOME_DIR = os.path.expanduser("~")
HERMES_USER = os.environ.get("HERMES_USER", pwd.getpwuid(os.getuid()).pw_name)
HERMES_HOME = os.environ.get("HERMES_HOME", os.path.join(HOME_DIR, ".hermes"))   # ★ 必须是 .hermes（账号目录拼接不含 .hermes）
WRONG_DIR = os.path.join(HOME_DIR, "weixin")       # 错误路径残留（首版脚本写错过）
QR_PNG = os.path.join(HOME_DIR, "wx-fix-qr.png")   # 二维码 PNG（可用 sftp 下载放大扫）
QR_TXT = os.path.join(HOME_DIR, "wx-fix-qr.txt")   # 二维码 liteapp URL
LOG_FILE = os.path.join(HOME_DIR, "wx-fix.log")

# Hermes venv 的 python 与 gateway 模块
HERMES_VENV = os.environ.get("HERMES_VENV", os.path.join(HOME_DIR, "hermes-venv"))
sys.path.insert(0, os.path.join(HERMES_VENV, "lib", "python3.11", "site-packages"))
from gateway.platforms import weixin as W  # noqa: E402

TOTAL_TIMEOUT = 480   # 等扫码总超时（秒）
QR_REFRESH_MAX = 3    # 二维码过期自动刷新上限

pw = pwd.getpwnam(HERMES_USER)


def log(msg):
    line = f"[{time.strftime('%H:%M:%S')}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(line + "\n")


def wj(path, data):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False)
    os.replace(tmp, path)


def chown_hermes(path):
    try:
        os.chown(path, pw.pw_uid, pw.pw_gid)
    except OSError:
        pass


def check_weixin_healthy():
    """sync.json mtime 近 60 秒有更新 = 长轮询正常 = 微信是通的"""
    acc_dir = os.path.join(HERMES_HOME, "weixin", "accounts")
    if not os.path.isdir(acc_dir):
        return False, "账号目录不存在"
    syncs = [f for f in os.listdir(acc_dir) if f.endswith("@im.bot.sync.json")]
    if not syncs:
        return False, "无 sync 游标文件"
    latest = max(os.path.getmtime(os.path.join(acc_dir, f)) for f in syncs)
    age = time.time() - latest
    return age < 60, f"sync 游标 {age:.0f} 秒前更新过"


def find_gateway_pids():
    out = subprocess.run(
        ["ps", "aux"], capture_output=True, text=True).stdout
    pids = []
    for ln in out.splitlines():
        if "hermes-venv/bin/python" in ln and "gateway" in ln and "grep" not in ln:
            pids.append(ln.split()[1])
    return pids


async def fetch_qr(session):
    qr = await W._api_get(
        session, base_url=W.ILINK_BASE_URL,
        endpoint=f"{W.EP_GET_BOT_QR}?bot_type=3", timeout_ms=35000)
    return str(qr.get("qrcode") or ""), str(qr.get("qrcode_img_content") or ""), qr


def show_qr(url_text):
    """终端 ASCII 二维码 + 存 PNG + 存 URL 文本"""
    try:
        import qrcode
        qr = qrcode.QRCode(border=2, box_size=1)
        qr.add_data(url_text)
        qr.make(fit=True)
        # PNG（供 sftp 下载放大扫）
        img = qr.make_image()
        img.save(QR_PNG)
        chown_hermes(QR_PNG)
        log(f"二维码 PNG 已存: {QR_PNG}（可下载放大后用微信扫）")
        # 终端 ASCII
        print("\n" + "=" * 46)
        print("  请用手机微信「扫一扫」扫描下方二维码：")
        print("=" * 46)
        qr.print_ascii(invert=True)
        print("=" * 46 + "\n")
    except Exception as e:
        log(f"二维码渲染失败({e})，改用链接方式")
        print(f"\n请在微信中打开此链接完成绑定:\n{url_text}\n")
    with open(QR_TXT, "w", encoding="utf-8") as f:
        f.write(url_text)
    chown_hermes(QR_TXT)


async def relogin_flow():
    """扫码登录主流程，返回 (account_id, token, base_url, user_id) 或 None"""
    deadline = time.monotonic() + TOTAL_TIMEOUT
    refresh = 0
    async with aiohttp.ClientSession(trust_env=True,
                                     connector=W._make_ssl_connector()) as session:
        while True:
            try:
                qv, qu, raw = await fetch_qr(session)
            except Exception as e:
                log(f"拉二维码失败: {e}")
                return None
            if not qv:
                log(f"响应无二维码: {str(raw)[:200]}")
                return None
            show_qr(qu)
            log("等待扫码（二维码约 2 分钟过期，过期自动刷新）...")

            base = W.ILINK_BASE_URL
            qr_deadline = time.monotonic() + 150
            while time.monotonic() < qr_deadline and time.monotonic() < deadline:
                try:
                    r = await W._api_get(
                        session, base_url=base,
                        endpoint=f"{W.EP_GET_QR_STATUS}?qrcode={qv}",
                        timeout_ms=35000)
                except Exception:
                    await asyncio.sleep(2)
                    continue
                st = str(r.get("status") or "wait")
                if st != "wait":
                    log(f"扫码状态: {st}")
                if st == "scaned_but_redirect":
                    host = str(r.get("redirect_host") or "")
                    if host:
                        base = f"https://{host}"
                elif st == "confirmed":
                    account_id = str(r.get("ilink_bot_id") or "")
                    token = str(r.get("bot_token") or "")
                    base_url = str(r.get("baseurl") or W.ILINK_BASE_URL)
                    user_id = str(r.get("ilink_user_id") or "")
                    if not account_id or not token:
                        log("confirmed 但缺凭据字段")
                        return None
                    return account_id, token, base_url, user_id
                elif st == "expired":
                    refresh += 1
                    if refresh > QR_REFRESH_MAX:
                        log("二维码刷新超限，放弃")
                        return None
                    log(f"二维码过期，自动刷新第 {refresh} 次")
                    break  # 跳出内层，重新拉码
                await asyncio.sleep(1)
            else:
                continue
            # expired 时 break 到这里重新拉码
            continue
        return None


def install_credentials(account_id, token, base_url, user_id):
    """保存新凭据到正确目录 + 停用旧账号 + 更新 .env"""
    # 1. 保存新账号（用 Hermes 官方函数，落到 ~/.hermes/weixin/accounts/）
    W.save_weixin_account(HERMES_HOME, account_id=account_id, token=token,
                          base_url=base_url, user_id=user_id)
    log(f"新账号已保存: {account_id}")
    # 防御：无论以什么用户运行，账号文件属主归 hermes（gateway 以 hermes 跑）
    subprocess.run(["chown", "-R", f"{HERMES_USER}:{HERMES_USER}",
                    os.path.join(HERMES_HOME, "weixin")], capture_output=True)

    acc_dir = os.path.join(HERMES_HOME, "weixin", "accounts")

    # 2. 停用旧账号（非新账号的 json 文件加 .bak，幂等）
    for name in os.listdir(acc_dir):
        if name.startswith(account_id):
            continue
        if name.endswith(".bak"):
            continue
        if name.endswith(("@im.bot.json", "@im.bot.sync.json",
                          "@im.bot.context-tokens.json")):
            p = os.path.join(acc_dir, name)
            shutil.move(p, p + ".bak")
            log(f"旧账号文件停用: {name} -> {name}.bak")

    # 3. 清错误路径残留
    if os.path.isdir(WRONG_DIR) and not os.listdir(os.path.join(WRONG_DIR, "accounts")):
        shutil.rmtree(WRONG_DIR)
        log(f"清理错误目录: {WRONG_DIR}")

    # 4. 更新 .env（备份 → 替换 WEIXIN_ACCOUNT_ID / WEIXIN_TOKEN）
    env_path = os.path.join(HERMES_HOME, ".env")
    stamp = time.strftime("%Y%m%d-%H%M%S")
    shutil.copy(env_path, f"{env_path}.bak-{stamp}")
    with open(env_path, encoding="utf-8") as f:
        lines = f.read().splitlines()
    out, hit_id, hit_tok = [], False, False
    for ln in lines:
        if ln.startswith("WEIXIN_ACCOUNT_ID="):
            out.append(f"WEIXIN_ACCOUNT_ID={account_id}")
            hit_id = True
        elif ln.startswith("WEIXIN_TOKEN="):
            out.append(f"WEIXIN_TOKEN={token}")
            hit_tok = True
        else:
            out.append(ln)
    if not hit_id:
        out.append(f"WEIXIN_ACCOUNT_ID={account_id}")
    if not hit_tok:
        out.append(f"WEIXIN_TOKEN={token}")
    with open(env_path, "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    os.chmod(env_path, 0o600)
    chown_hermes(env_path)
    log(f".env 已更新（备份 .env.bak-{stamp}），当前账号: {account_id}")


def restart_gateway():
    """kill 现有 gateway，等 watchdog 拉起（最多等 75 秒）"""
    pids = find_gateway_pids()
    if pids:
        for p in pids:
            subprocess.run(["kill", p], capture_output=True)
        log(f"已发送终止信号给 gateway PID {','.join(pids)}，等待 watchdog 自动拉起...")
    else:
        log("gateway 未在运行，等待 watchdog 拉起...")
    for i in range(15):
        time.sleep(5)
        new = find_gateway_pids()
        if new:
            log(f"✅ gateway 已由 watchdog 拉起 (PID {','.join(new)})")
            return True
    log("⚠️ watchdog 75 秒内未拉起 gateway，请手动执行:")
    log(f"su - {HERMES_USER} -c 'source ~/{os.path.basename(HERMES_VENV)}/bin/activate && cd ~ && setsid nohup hermes gateway run >> ~/hermes-gateway.log 2>&1 </dev/null &'")
    return False


def verify():
    """验证 sync.json 是否持续更新"""
    acc_dir = os.path.join(HERMES_HOME, "weixin", "accounts")
    syncs = [f for f in os.listdir(acc_dir) if f.endswith("@im.bot.sync.json")]
    if not syncs:
        return False
    p = os.path.join(acc_dir, syncs[0])
    t1 = os.path.getmtime(p)
    log("验证中：等待 25 秒观察 sync 游标...")
    time.sleep(25)
    t2 = os.path.getmtime(p)
    if t2 > t1:
        log(f"✅ sync 游标持续更新（{t2 - t1:.0f} 秒前跳动）—— 微信长轮询正常")
        return True
    log("⚠️ sync 游标 25 秒未跳动，可能仍未恢复")
    return False


def main():
    log("========== 微信一键恢复开始 ==========")
    healthy, why = check_weixin_healthy()
    if healthy:
        print("\n当前微信通道正常（" + why + "），无需修复。")
        ans = input("仍要重新扫码换新账号吗？(y/N): ").strip().lower()
        if ans != "y":
            log("用户取消，退出")
            return
        log("用户选择强制重扫")
    else:
        log(f"检测到微信异常：{why}，进入恢复流程")

    cred = asyncio.run(relogin_flow())
    if not cred:
        log("❌ 扫码流程未完成（超时或失败），请重跑本脚本。")
        return
    account_id, token, base_url, user_id = cred
    log(f"扫码成功！新账号: {account_id}")
    install_credentials(account_id, token, base_url, user_id)
    restart_gateway()
    verify()
    log("========== 流程结束 ==========")
    print(f"\n如果上面有 ❌ 或 ⚠️，把 {LOG_FILE} 的内容发给我看。")


if __name__ == "__main__":
    main()
