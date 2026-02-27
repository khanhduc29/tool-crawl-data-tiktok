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
    stable_rounds = 0

    for round_idx in range(12):
        logger.info(f"🔄 Scroll search round {round_idx + 1}")

        links = page.locator("a[href*='/video/']")
        count = await links.count()
        logger.info(f"🎞 Video links visible: {count}")

        for i in range(count):
            href = await links.nth(i).get_attribute("href")
            if not href:
                continue

            video_id = extract_video_id(href)
            if not video_id or video_id in seen:
                continue

            seen.add(video_id)
            video_url = normalize_tiktok_url(href)

            results.append({
                "video_id": video_id,
                "video_url": video_url,

            })
            logger.info(f"🎬 Found video: {video_id}")

            if len(results) >= limit:
                return results

        before = len(seen)

        # 🔽 scroll đúng cách
        await auto_scroll_video(page, steps=2)

        # ⏳ chờ TikTok load batch mới
        await page.wait_for_timeout(4000)

        after = len(seen)

        if after == before:
            stable_rounds += 1
            logger.info(f"⚠ No new videos round {stable_rounds}")
        else:
            stable_rounds = 0

        # ⛔ dừng khi TikTok thật sự không load nữa
        if stable_rounds >= 4:
            logger.info("🛑 TikTok stopped loading new videos")
            break

    return results


# =========================
# VIDEO DETAIL
# =========================
async def crawl_video_detail(page, scan_account, keyword, video_url):
    logger.info(f"🎥 Open video: {video_url}")

    await page.goto(video_url, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    caption = None
    if await page.locator("h1").count() > 0:
        caption = await page.locator("h1").first.inner_text()

    stats = page.locator("strong[data-e2e$='count']")
    texts = []
    for i in range(await stats.count()):
        texts.append(await stats.nth(i).inner_text())

    view_count = parse_number(texts[0]) if len(texts) > 0 else None
    like_count = parse_number(texts[1]) if len(texts) > 1 else None
    comment_count = parse_number(texts[2]) if len(texts) > 2 else None
    share_count = parse_number(texts[3]) if len(texts) > 3 else None

    author_username = None
    author_el = page.locator("a[href^='/@']")
    if await author_el.count() > 0:
        href = await author_el.first.get_attribute("href")
        if href:
            author_username = href.replace("/@", "").split("/")[0]

    return {
        "scan_account": scan_account,
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
    scan_account,
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
                    page, scan_account, keyword, video["video_url"]
                )
                video.update(detail)
            else:
                video.update({
                    "scan_account": scan_account,
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

    save_to_json(f"top_posts_{keyword}.json", results)
    save_to_csv(f"top_posts_{keyword}.csv", results)

    logger.info(f"🏁 Hoàn thành – tổng video: {len(results)}")
    return results