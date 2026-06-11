"""
check_cookie.py
检查 .env 中的知乎 Cookie 是否有效。

用法：
    python check_cookie.py

退出码：
    0 - Cookie 有效
    1 - Cookie 无效或缺失
"""

from __future__ import annotations

import os
import sys

import requests
from dotenv import load_dotenv

load_dotenv()

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/147.0.0.0 Safari/537.36"
    ),
}

API = os.getenv("API", "https://www.zhihu.com/api/v4")


def check_cookie() -> bool:
    """检查 Cookie 是否有效。返回 True 表示有效。"""
    cookie = os.getenv("COOKIE_A") or os.getenv("COOKIE_B")
    if not cookie:
        print("COOKIE_A 或 COOKIE_B 未设置")
        return False

    print(f"正在检查 Cookie（长度：{len(cookie)} 字符）...")

    try:
        resp = requests.get(
            f"{API}/me",
            headers={**HEADERS, "Cookie": cookie},
            timeout=10,
        )
        data = resp.json()
    except Exception as exc:
        print(f"请求失败：{exc}")
        return False

    if "error" in data:
        err = data["error"]
        code = err.get("code", 0)
        msg = err.get("message", "")
        if code == 10003 or "未登录" in msg or "unauthorized" in msg.lower():
            print(f"Cookie 已失效（code={code}）：{msg}")
        else:
            print(f"API 返回错误（code={code}）：{msg}")
        return False

    name = data.get("name", "未知")
    print(f"Cookie 有效，登录用户：{name}")
    return True


if __name__ == "__main__":
    ok = check_cookie()
    sys.exit(0 if ok else 1)
