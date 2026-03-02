import re
import json
import csv
import os
import random
from core.logger import setup_logger

logger = setup_logger()
DATA_DIR = "data"


# =========================
# UTILS
# =========================
def parse_number(text: str | None):
    if not text:
        return None

    text = text.strip().upper()

    try:
        if text.endswith("M"):
            return int(float(text[:-1]) * 1_000_000)
        if text.endswith("K"):
            return int(float(text[:-1]) * 1_000)
        return int(re.sub(r"[^\d]", "", text))
    except Exception:
        return None


def extract_video_id(url: str):
    if not url:
        return None
    m = re.search(r"/video/(\d+)", url)
    return m.group(1) if m else None


def save_to_json(filename, data):
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"💾 Saved JSON: {path}")


def save_to_csv(filename, data):
    if not data:
        return
    os.makedirs(DATA_DIR, exist_ok=True)
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    logger.info(f"📊 Saved CSV: {path}")


# =========================
# SCROLL – DỨT ĐIỂM
# =========================
async def auto_scroll_video(page, steps=2):
    """
    Scroll giống người thật:
    - scroll nhỏ
    - chờ lâu
    - dùng document.scrollingElement
    """
    for _ in range(steps):
        await page.evaluate("""
            () => {
                const el = document.scrollingElement || document.documentElement;
                el.scrollBy(0, window.innerHeight * 0.8);
            }
        """)
        # ⚠️ bắt buộc chờ đủ lâu
        await page.wait_for_timeout(3000)

def normalize_tiktok_url(href: str | None):
    """
    Chuẩn hoá link video TikTok:
    - Nếu đã là absolute → dùng nguyên
    - Nếu là relative → prepend domain
    """
    if not href:
        return None

    href = href.strip()

    if href.startswith("http"):
        return href

    if href.startswith("/"):
        return f"https://www.tiktok.com{href}"

    return None
# =========================
# SEARCH → VIDEO LIST
# =========================
async def extract_top_videos(page, keyword, limit):
    url = f"https://www.tiktok.com/search/video?q={keyword}"
    logger.info(f"🌐 Open search video URL: {url}")

    await page.goto(url, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_timeout(5000)

    results = []
    seen = set()

    for round_idx in range(12):
        logger.info(f"🔄 Scroll search round {round_idx + 1}")

        cards = page.locator("a[href*='/video/']")
        count = await cards.count()

        for i in range(count):
            card = cards.nth(i)
            href = await card.get_attribute("href")
            if not href:
                continue

            video_id = extract_video_id(href)
            if not video_id or video_id in seen:
                continue

            seen.add(video_id)
            video_url = normalize_tiktok_url(href)

            # ===== thumbnail =====
            thumb = None
            img = card.locator("img[src*='tiktokcdn.com']")
            if await img.count() > 0:
                thumb = await img.first.get_attribute("src")

            # ===== view count =====
            view_count = None
            view_el = card.locator("strong[data-e2e='video-views']")
            if await view_el.count() > 0:
                view_count = parse_number(await view_el.first.inner_text())

            results.append({
                "video_id": video_id,
                "video_url": video_url,
                "thumbnail": thumb,
                "view_count": view_count,
            })

            logger.info(f"🎬 Found video: {video_id}")

            if len(results) >= limit:
                return results

        await auto_scroll_video(page, steps=2)
        await page.wait_for_timeout(4000)

    return results


# =========================
# VIDEO DETAIL
# =========================
async def crawl_video_detail(page, keyword, video_url):
    logger.info(f"🎥 Open video: {video_url}")

    await page.goto(video_url, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    # ===== caption =====
    caption = None
    h1 = page.locator("h1")
    if await h1.count() > 0:
        caption = await h1.first.inner_text()

    # ===== stats =====
    async def get_stat(label):
        el = page.locator(f"strong[data-e2e='{label}']")
        if await el.count() > 0:
            text = await el.first.inner_text()
            return parse_number(text)
        return None

    view_count = await get_stat("view-count")
    like_count = await get_stat("like-count")
    comment_count = await get_stat("comment-count")
    share_count = await get_stat("share-count")

    # ===== author =====
    author_username = None
    author = page.locator("a[href^='/@']")
    if await author.count() > 0:
        href = await author.first.get_attribute("href")
        author_username = href.replace("/@", "").split("/")[0]

    return {
        "keyword": keyword,

        "video_url": video_url,
        "caption": caption,

        "author_username": author_username,
        "author_profile": (
            f"https://www.tiktok.com/@{author_username}"
            if author_username else None
        ),

        "view_count": view_count,
        "like_count": like_count,
        "comment_count": comment_count,
        "share_count": share_count,
    }

# =========================
# MAIN
# =========================
async def crawl_top_posts(
    page,
    keyword,
    sort_by="view",
    limit=50,

    delay_range=(3000, 6000),
    batch_size=5,
    batch_delay=8000,
    deep_scan=False,
    **kwargs,
):
    results = []

    videos = await extract_top_videos(page, keyword, limit)
    logger.info(f"📋 Tổng video lấy được: {len(videos)}")

    for idx, video in enumerate(videos, 1):
        try:
            if deep_scan:
                detail = await crawl_video_detail(
                    page,  keyword, video["video_url"]
                )
                video.update(detail)
            else:
                video.update({
                    "keyword": keyword,
                })

            results.append(video)

        except Exception as e:
            logger.warning(f"❌ Skip video | {e}")

        await page.wait_for_timeout(random.randint(*delay_range))

        if idx % batch_size == 0:
            logger.info("🧘 Batch pause...")
            await page.wait_for_timeout(batch_delay)

        if len(results) >= limit:
            break

    # ===== sort (chỉ có ý nghĩa khi deep_scan) =====
    if deep_scan:
        sort_key = {
            "view": "view_count",
            "like": "like_count",
            "comment": "comment_count",
        }.get(sort_by)

        if sort_key:
            results.sort(
                key=lambda x: x.get(sort_key) or 0,
                reverse=True
            )

    # save_to_json(f"top_posts_{keyword}.json", results)
    # save_to_csv(f"top_posts_{keyword}.csv", results)

    logger.info(f"🏁 Hoàn thành – tổng video: {len(results)}")
    return results