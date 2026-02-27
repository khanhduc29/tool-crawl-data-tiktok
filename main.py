
import asyncio
import json
from pathlib import Path

from core.browser import create_browser
from crawlers.scan_top_posts import crawl_top_posts
from crawlers.search_user import crawl_users_by_keyword
from core.logger import setup_logger
from crawlers.scan_relations import crawl_relations
from crawlers.scan_video_comments import crawl_video_comments

logger = setup_logger()
SESSION_FILE = "tiktok_session.json"


def load_config(form_name: str):
    base_dir = Path(__file__).resolve().parent
    config_path = base_dir / "configs" / f"{form_name}.json"

    if not config_path.exists():
        raise FileNotFoundError(f"❌ Không tìm thấy config: {config_path}")

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    if "delay_range" in config:
        config["delay_range"] = tuple(config["delay_range"])

    return config

async def main():
    logger.info("🚀 START TIKTOK CRAWLER")

    # FORM = "scan_users"
    # FORM = "scan_relations"
    # FORM = "scan_video_comments"
    FORM = "scan_top_posts"

    CONFIG = load_config(FORM)

    playwright, browser, context, page = await create_browser(
        headless=False,
        session_file=SESSION_FILE
    )

    try:
        if FORM == "scan_users":
            result = await crawl_users_by_keyword(page=page, **CONFIG)

        elif FORM == "scan_relations":
            result = await crawl_relations(page=page, **CONFIG)

        elif FORM == "scan_video_comments":
            result = await crawl_video_comments(page=page, **CONFIG)
        elif FORM == "scan_top_posts":
            result = await crawl_top_posts(page=page, **CONFIG)
        else:
            raise ValueError("❌ Form không hợp lệ")
        logger.info("📦 KẾT QUẢ CUỐI CÙNG:")
        logger.info(json.dumps(result, indent=2, ensure_ascii=False))

    except Exception as e:
        logger.exception(f"❌ ERROR: {e}")

    finally:
        await context.close()
        await browser.close()
        await playwright.stop()
        logger.info("🛑 STOP CRAWLER")


if __name__ == "__main__":
    asyncio.run(main())
