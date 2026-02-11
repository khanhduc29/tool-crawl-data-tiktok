import os
from playwright.async_api import async_playwright


async def create_browser(headless=True, session_file=None):
    playwright = await async_playwright().start()

    browser = await playwright.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )

    # ===== TẠO CONTEXT =====
    context_kwargs = {
        "user_agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "viewport": {"width": 1280, "height": 800},
    }

    # 👉 nếu có session thì dùng, không có thì bỏ qua
    if session_file and os.path.exists(session_file):
        context_kwargs["storage_state"] = session_file

    context = await browser.new_context(**context_kwargs)

    page = await context.new_page()

    return playwright, browser, context, page
