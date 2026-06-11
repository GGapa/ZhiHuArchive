import subprocess
import sys


def run(script: str) -> None:
    print(f"\n{'='*40}")
    print(f"Running {script}...")
    print('='*40)
    result = subprocess.run([sys.executable, script], check=True)


def check_cookie() -> bool:
    """检查 Cookie 是否有效，无效时打印错误并返回 False。"""
    import os

    import requests
    from dotenv import load_dotenv

    load_dotenv()
    cookie = os.getenv("COOKIE_A") or os.getenv("COOKIE_B")
    api = os.getenv("API", "https://www.zhihu.com/api/v4")

    if not cookie:
        print("ERROR: COOKIE_A 或 COOKIE_B 未设置，请先在 .env 中配置知乎 Cookie。")
        print("提示：可以运行 fetch_zhihu_cookie.py 自动从浏览器提取 Cookie。")
        return False

    try:
        resp = requests.get(
            f"{api}/me",
            headers={
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/147.0.0.0 Safari/537.36"
                ),
                "Cookie": cookie,
            },
            timeout=10,
        )
        data = resp.json()
    except Exception as exc:
        print(f"ERROR: 检查 Cookie 时请求失败：{exc}")
        return False

    if "error" in data:
        err = data["error"]
        code = err.get("code", 0)
        msg = err.get("message", "")
        print(f"ERROR: Cookie 已失效（code={code}）：{msg}")
        print("请更新 .env 中的 Cookie，或运行 fetch_zhihu_cookie.py 自动提取。")
        return False

    name = data.get("name", "未知")
    print(f"Cookie 验证通过，登录用户：{name}")
    return True


def main() -> None:
    if not check_cookie():
        sys.exit(1)
    run("get_list.py")
    run("csv2path.py")
    run("download.py")
    run("radar.py")


if __name__ == "__main__":
    main()
