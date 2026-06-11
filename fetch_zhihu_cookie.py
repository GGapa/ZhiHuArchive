"""
fetch_zhihu_cookie.py
从 Windows 本地浏览器的 Cookie 数据库自动提取知乎 Cookie。

支持的浏览器：Google Chrome、Microsoft Edge、Brave
依赖：pywin32（仅 Windows 需要）

用法：
    python fetch_zhihu_cookie.py
    python fetch_zhihu_cookie.py --output .env --format env
    python fetch_zhihu_cookie.py --key COOKIE_B --output .env
"""

from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path

ZHIHU_HOST = "%zhihu.com%"


def get_browser_paths() -> list[tuple[str, Path]]:
    """返回所有检测到的浏览器名称和 Cookie 数据库路径。"""
    local = Path(os.environ.get("LOCALAPPDATA", ""))
    if not local:
        return []

    candidates: list[tuple[str, Path]] = [
        ("Chrome",  local / "Google" / "Chrome" / "User Data" / "Default" / "Cookies"),
        ("Chrome",  local / "Google" / "Chrome" / "User Data" / "Default" / "Network" / "Cookies"),
        ("Edge",    local / "Microsoft" / "Edge" / "User Data" / "Default" / "Cookies"),
        ("Edge",    local / "Microsoft" / "Edge" / "User Data" / "Default" / "Network" / "Cookies"),
        ("Brave",   local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Cookies"),
        ("Brave",   local / "BraveSoftware" / "Brave-Browser" / "User Data" / "Default" / "Network" / "Cookies"),
    ]
    seen: set[Path] = set()
    result: list[tuple[str, Path]] = []
    for name, p in candidates:
        if p.exists() and p not in seen:
            seen.add(p)
            result.append((name, p))
    return result


def decrypt_dpapi(encrypted: bytes) -> str:
    """用 Windows DPAPI 解密 Chrome/Edge 加密的 Cookie 值。"""
    try:
        import win32crypt  # type: ignore[import-untyped]
        data = win32crypt.CryptUnprotectData(encrypted, None, None, None, 0)
        return data[1].decode("utf-8", errors="replace")
    except ImportError:
        print("缺少 pywin32 库，请运行: pip install pywin32", file=sys.stderr)
        sys.exit(1)
    except Exception:
        return ""


def extract_cookies(db_path: Path) -> dict[str, str]:
    """从浏览器 Cookie 数据库提取知乎相关 Cookie。"""
    # 浏览器可能锁定数据库，复制后读取
    tmp = Path(tempfile.gettempdir()) / "zhihu_cookies_tmp.db"
    shutil.copy2(db_path, tmp)

    try:
        conn = sqlite3.connect(str(tmp))
        cur = conn.cursor()
        cur.execute(
            "SELECT name, encrypted_value, value FROM cookies WHERE host_key LIKE ?",
            (ZHIHU_HOST,),
        )
        cookies: dict[str, str] = {}
        for name, encrypted_value, value in cur.fetchall():
            if value:
                cookies[name] = value
            elif encrypted_value:
                decrypted = decrypt_dpapi(encrypted_value)
                if decrypted:
                    cookies[name] = decrypted
        conn.close()
    finally:
        tmp.unlink(missing_ok=True)

    return cookies


def format_cookie(cookies: dict[str, str]) -> str:
    return "; ".join(f"{k}={v}" for k, v in cookies.items())


def write_env(cookie_str: str, output: Path, key: str) -> None:
    """将 Cookie 写入 .env 文件，保留其他已有配置。"""
    lines: list[str] = []
    if output.exists():
        for line in output.read_text(encoding="utf-8").splitlines():
            if not line.strip().startswith(f"{key}="):
                lines.append(line)
    lines.append(f'{key}="{cookie_str}"')
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="从浏览器自动提取知乎 Cookie",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""\
示例:
  python fetch_zhihu_cookie.py
  python fetch_zhihu_cookie.py --output .env --format env
  python fetch_zhihu_cookie.py --key COOKIE_B --output .env
""",
    )
    parser.add_argument("-o", "--output", type=Path, default=None,
                        help="输出文件路径（如 .env），不指定则打印到终端")
    parser.add_argument("--format", choices=["env", "raw"], default="raw",
                        help="输出格式：env（COOKIE_A=\"...\"）或 raw（默认）")
    parser.add_argument("--key", default="COOKIE_A",
                        help="写入 .env 时使用的变量名（默认：COOKIE_A）")
    args = parser.parse_args()

    print("=" * 50)
    print("知乎 Cookie 提取工具")
    print("=" * 50)

    # 检测浏览器
    browsers = get_browser_paths()
    if not browsers:
        print("未找到支持的浏览器 Cookie 数据库。")
        print("支持的浏览器：Google Chrome、Microsoft Edge、Brave")
        print("请确认浏览器已安装并登录 https://www.zhihu.com")
        sys.exit(1)

    # 优先使用第一个检测到的浏览器
    browser_name, db_path = browsers[0]
    if len(browsers) > 1:
        names = ", ".join(n for n, _ in browsers)
        print(f"检测到多个浏览器：{names}，使用 {browser_name}")
    else:
        print(f"检测到浏览器：{browser_name}")
    print(f"Cookie 数据库：{db_path}")

    # 提取
    print("\n正在提取知乎 Cookie...")
    cookies = extract_cookies(db_path)
    if not cookies:
        print("未提取到任何知乎 Cookie。")
        print("请先在浏览器中登录 https://www.zhihu.com，然后重试。")
        sys.exit(1)

    print(f"提取到 {len(cookies)} 个 Cookie")
    key_names = [k for k in ("z_c0", "SESSIONID", "_zap", "JOID", "osd") if k in cookies]
    other_names = [k for k in cookies if k not in key_names]
    if key_names:
        print(f"  关键 Cookie: {', '.join(key_names)}")
    if other_names:
        shown = other_names[:5]
        suffix = "..." if len(other_names) > 5 else ""
        print(f"  其他 Cookie: {', '.join(shown)}{suffix}")

    cookie_str = format_cookie(cookies)
    print(f"  总长度: {len(cookie_str)} 字符")

    # 输出
    if args.output:
        if args.format == "env":
            write_env(cookie_str, args.output, args.key)
            print(f"\nCookie 已写入：{args.output}（变量名：{args.key}）")
        else:
            args.output.write_text(cookie_str, encoding="utf-8")
            print(f"\nCookie 已写入：{args.output}")
    else:
        print("\n" + "-" * 50)
        if args.format == "env":
            print(f'{args.key}="{cookie_str}"')
        else:
            print(cookie_str)
        print("-" * 50)
        print("\n将以上内容填入 .env 文件中。")
        print("  或使用 --output .env --format env 直接写入。")


if __name__ == "__main__":
    main()
