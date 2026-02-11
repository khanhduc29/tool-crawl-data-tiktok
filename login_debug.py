import asyncio
import json
from playwright.async_api import async_playwright

SESSION_FILE = "tiktok_session.json"


async def login_debug():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
            ],
        )

        context = await browser.new_context(
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        )

        page = await context.new_page()

        # ===== LOG CONSOLE =====
        page.on(
            "console",
            lambda msg: print(f"[CONSOLE {msg.type.upper()}] {msg.text}"),
        )

        # ===== PAGE ERROR =====
        page.on(
            "pageerror",
            lambda err: print(f"[PAGE ERROR] {err}"),
        )

        # ===== REQUEST FAILED =====
        def on_request_failed(req):
            print("[REQUEST FAILED]")
            print("  URL :", req.url)
            print("  ERR :", req.failure)

        page.on("requestfailed", on_request_failed)

        # ===== RESPONSE ERROR =====
        def on_response(res):
            if res.status >= 400:
                print("[RESPONSE ERROR]")
                print("  STATUS:", res.status)
                print("  URL   :", res.url)

        page.on("response", on_response)

        print("🌐 Opening TikTok...")
        await page.goto("https://www.tiktok.com", timeout=60000)

        # đợi trang ổn định
        await page.wait_for_load_state("networkidle")
        await page.wait_for_timeout(5000)

        print("\n🧪 DEBUG CHECK:")
        print("- URL  :", page.url)
        print("- Title:", await page.title())

        # ✅ FIX LỖI Ở ĐÂY
        html = await page.content()
        html = html.lower()

        if "captcha" in html:
            print("❌ CAPTCHA PAGE DETECTED")

        if "verify" in html or "security" in html:
            print("⚠️ SECURITY VERIFY PAGE")

        if "login" in page.url:
            print("ℹ️ LOGIN PAGE DETECTED (URL)")

        print("\n👉 Hãy LOGIN thủ công trên trình duyệt")
        print("👉 Xong thì quay lại terminal và bấm ENTER")
        input()

        print("\n📦 Saving session...")
        storage = await context.storage_state()
        with open(SESSION_FILE, "w", encoding="utf-8") as f:
            json.dump(storage, f, ensure_ascii=False, indent=2)

        print(f"✅ Session saved: {SESSION_FILE}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(login_debug())
