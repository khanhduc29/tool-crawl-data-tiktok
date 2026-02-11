import re
import json
import csv
import os
from core.utils import auto_scroll
from schemas.user import TikTokUser
from core.logger import setup_logger
import random

logger = setup_logger()

DATA_DIR = "data"


# =========================
# UTILS
# =========================
def parse_number(text: str):
    if not text:
        return None
    text = text.strip().upper()
    if text.endswith("M"):
        return int(float(text[:-1]) * 1_000_000)
    if text.endswith("K"):
        return int(float(text[:-1]) * 1_000)
    return int(re.sub(r"[^\d]", "", text))


def detect_language(text: str):
    if not text:
        return "unknown"
    vi_chars = "ăâđêôơưáàảãạ"
    if any(c in text.lower() for c in vi_chars):
        return "vi"
    return "en"


def detect_country(bio, external_link):
    text = (bio or "").lower()
    if any(x in text for x in ["việt", "vn", "hà nội", "sài gòn", "tp.hcm"]):
        return "VN"
    if external_link and ".vn" in external_link:
        return "VN"
    return "unknown"


def detect_account_type(username, bio, external_link):
    bio_lower = (bio or "").lower()

    if external_link:
        if any(x in external_link for x in ["shop", "store", "linktr.ee", "beacons"]):
            return "commercial"

    if any(x in bio_lower for x in ["shop", "order", "booking", "email", "contact"]):
        return "commercial"

    if username.isdigit():
        return "personal"

    return "creator"


# =========================
# SAVE FILE
# =========================
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
# SEARCH → USERNAME
# =========================
async def extract_usernames_from_search(page, keyword, limit):
    url = f"https://www.tiktok.com/search/user?q={keyword}"
    logger.info(f"🌐 Open search URL: {url}")

    await page.goto(url, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_timeout(4000)

    usernames = []
    seen = set()

    for round_idx in range(6):
        logger.info(f"🔄 Scroll search round {round_idx + 1}")
        await auto_scroll(page, 2)
        await page.wait_for_timeout(2000)

        links = page.locator("a[href^='/@']")
        count = await links.count()
        logger.info(f"🔗 Total /@ links found: {count}")

        for i in range(count):
            link = links.nth(i)

            # chỉ giữ user card (có Followers)
            if await link.locator("p:has-text('Followers')").count() == 0:
                continue

            href = await link.get_attribute("href")
            if not href:
                continue

            username = href.replace("/@", "").split("/")[0]
            if not username or username in seen:
                continue

            seen.add(username)
            usernames.append(username)
            logger.info(f"🔎 Found username: @{username}")

            if len(usernames) >= limit:
                return usernames

    return usernames


# =========================
# PROFILE → DATA
# =========================
async def crawl_profile(page, scan_account, keyword, username):
    url = f"https://www.tiktok.com/@{username}"
    logger.info(f"👤 Open profile: {url}")

    await page.goto(url, timeout=60000, wait_until="domcontentloaded")
    await page.wait_for_selector("h1[data-e2e='user-title']", timeout=20000)

    display_name = await page.locator(
        "h2[data-e2e='user-subtitle']"
    ).inner_text()

    bio = await page.locator(
        "h2[data-e2e='user-bio']"
    ).inner_text()

    followers = parse_number(
        await page.locator("strong[data-e2e='followers-count']").inner_text()
    )

    following = parse_number(
        await page.locator("strong[data-e2e='following-count']").inner_text()
    )

    avatar = None
    avatar_el = page.locator("img[src*='tiktokcdn']")
    if await avatar_el.count() > 0:
        avatar = await avatar_el.first.get_attribute("src")

    external_link = None
    link_el = page.locator("a[data-e2e='user-link']")
    if await link_el.count() > 0:
        external_link = await link_el.first.get_attribute("href")

    account_type = detect_account_type(username, bio, external_link)
    country = detect_country(bio, external_link)
    language = detect_language(bio)

    return {
        "scan_account": scan_account,
        "keyword": keyword,
        "tiktok_id": username,
        "username": username,
        "display_name": display_name,
        "bio": bio,
        "avatar_url": avatar,
        "profile_url": url,

        "account_type": account_type,
        "country": country,
        "primary_language": language,

        "follower_count": followers,
        "following_count": following,

        "external_link": external_link,
        "engagement_rate": None  # enrich ở bước sau
    }


# =========================
# MAIN
# =========================
async def crawl_users_by_keyword(
    page,
    scan_account,
    keyword,
    limit=50,

    # ===== config =====
    delay_range=(2000, 4000),
    batch_size=5,
    batch_delay=6000,
    deep_scan=True
):
    results = []

    usernames = await extract_usernames_from_search(page, keyword, limit)
    logger.info(f"📋 Tổng username lấy được: {len(usernames)}")

    for idx, username in enumerate(usernames, 1):
        try:
            if deep_scan:
                user_data = await crawl_profile(
                    page, scan_account, keyword, username
                )
            else:
                # scan nhẹ – chỉ lấy username
                user_data = {
                    "scan_account": scan_account,
                    "keyword": keyword,
                    "tiktok_id": username,
                    "username": username,
                    "profile_url": f"https://www.tiktok.com/@{username}"
                }

            logger.info(
                f"✅ USER @{username} | followers={user_data.get('follower_count')}"
            )
            results.append(user_data)

        except Exception as e:
            logger.warning(f"❌ Skip @{username} | {e}")

        # ===== human delay =====
        await page.wait_for_timeout(
            random.randint(*delay_range)
        )

        # ===== nghỉ theo batch =====
        if idx % batch_size == 0:
            logger.info("🧘 Batch pause...")
            await page.wait_for_timeout(batch_delay)

        if len(results) >= limit:
            break

    save_to_json(f"users_{keyword}.json", results)
    save_to_csv(f"users_{keyword}.csv", results)

    logger.info(f"🏁 Hoàn thành – tổng user: {len(results)}")
    return results

