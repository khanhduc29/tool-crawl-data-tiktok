import asyncio
import random


# ===========================
# UTILS
# ===========================

async def _random_delay(delay_range):
    await asyncio.sleep(random.uniform(*delay_range) / 1000)


# ===========================
# SCROLL LIST
# ===========================

async def _scroll_until_limit(page, limit, delay_range):
    users = set()

    print("🔎 Waiting for list container...")

    await page.wait_for_selector('[data-e2e="follow-info-popup"]')

    scroll_container = await page.query_selector(
        '[data-e2e="follow-info-popup"] div[class*="DivUserListContainer"]'
    )

    if not scroll_container:
        print("❌ Không tìm thấy DivUserListContainer")
        return []

    box = await scroll_container.bounding_box()
    if not box:
        print("❌ Không lấy được bounding box")
        return []

    await page.mouse.move(
        box["x"] + box["width"] / 2,
        box["y"] + box["height"] / 2
    )

    last_count = 0
    no_change_rounds = 0

    while len(users) < limit:
        links = await page.query_selector_all(
            '[data-e2e="follow-info-popup"] li a[href^="/@"]'
        )

        for link in links:
            href = await link.get_attribute("href")
            if href:
                users.add(href.replace("/@", "").strip())

        print(f"📊 Total collected: {len(users)}")

        for _ in range(5):
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.2)

        await asyncio.sleep(4)

        if len(users) == last_count:
            no_change_rounds += 1
            print(f"⚠ No change round: {no_change_rounds}")
        else:
            no_change_rounds = 0

        if no_change_rounds >= 3:
            print("🛑 Không load thêm → break")
            break

        last_count = len(users)

    return list(users)[:limit]


# ===========================
# FOLLOWERS
# ===========================

async def crawl_followers(page, username, limit, delay_range):
    print(f"\n🚀 Crawl followers của {username}")

    await page.goto(f"https://www.tiktok.com/@{username}")
    await page.wait_for_timeout(5000)

    btn = await page.query_selector('strong[data-e2e="followers-count"]')
    if not btn:
        return []

    await btn.click()
    await page.wait_for_selector('[data-e2e="follow-info-popup"]')

    tab = await page.query_selector(
        '[data-e2e="follow-info-popup"] strong[title="Followers"]'
    )
    if tab:
        await tab.click()
        await page.wait_for_timeout(2000)

    return await _scroll_until_limit(page, limit, delay_range)


# ===========================
# FOLLOWING
# ===========================

async def crawl_following(page, username, limit, delay_range):
    print(f"\n🚀 Crawl following của {username}")

    await page.goto(f"https://www.tiktok.com/@{username}")
    await page.wait_for_timeout(5000)

    btn = await page.query_selector('strong[data-e2e="following-count"]')
    if not btn:
        return []

    await btn.click()
    await page.wait_for_selector('[data-e2e="follow-info-popup"]')

    tab = await page.query_selector(
        '[data-e2e="follow-info-popup"] strong[title="Following"]'
    )
    if tab:
        await tab.click()
        await page.wait_for_timeout(2000)

    return await _scroll_until_limit(page, limit, delay_range)


# ===========================
# PROFILE DETAIL
# ===========================

async def crawl_profile_detail(page, username, delay_range):
    profile_url = f"https://www.tiktok.com/@{username}"
    print(f"👤 Crawl profile: {username}")

    await page.goto(profile_url, wait_until="domcontentloaded")
    await _random_delay(delay_range)

    try:
        await page.wait_for_selector(
            "script#__UNIVERSAL_DATA_FOR_REHYDRATION__",
            state="attached",
            timeout=10000
        )

        data = await page.evaluate("""
            () => {
                const el = document.querySelector(
                    'script#__UNIVERSAL_DATA_FOR_REHYDRATION__'
                );
                if (!el) return null;
                return JSON.parse(el.textContent);
            }
        """)

        if not data:
            return None

        user_info = data["__DEFAULT_SCOPE__"]["webapp.user-detail"]["userInfo"]
        user = user_info["user"]
        stats = user_info["stats"]

        return {
            "tiktok_id": user.get("id"),
            "username": user.get("uniqueId"),
            "display_name": user.get("nickname"),
            "bio": user.get("signature"),
            "avatar_url": user.get("avatarLarger"),
            "profile_url": profile_url,
            "follower_count": stats.get("followerCount"),
            "following_count": stats.get("followingCount"),
            "video_count": stats.get("videoCount"),
        }

    except Exception as e:
        print(f"❌ Profile parse error {username}: {e}")
        return None


# ===========================
# FRIENDS DETAIL
# ===========================

async def crawl_friends_detail(
    page,
    friends,
    delay_range,
    batch_size,
    batch_delay
):
    results = []

    for i in range(0, len(friends), batch_size):
        batch = friends[i:i + batch_size]
        print(f"\n📦 Friends batch {i // batch_size + 1}")

        for username in batch:
            detail = await crawl_profile_detail(page, username, delay_range)
            if detail:
                results.append(detail)

        if i + batch_size < len(friends):
            await asyncio.sleep(batch_delay / 1000)

    return results


# ===========================
# RELATIONS
# ===========================

async def crawl_relations(
    page,
    target_username,
    followers_limit,
    following_limit,
    delay_range,
    batch_size,
    batch_delay,
    calculate_friends=True,
    crawl_friends_detail_flag=True,
    **kwargs  # 👈 BẮT BUỘC
):
    followers = await crawl_followers(
        page, target_username, followers_limit, delay_range
    )

    await asyncio.sleep(batch_delay / 1000)

    following = await crawl_following(
        page, target_username, following_limit, delay_range
    )

    result = {
        "username": target_username,
        "followers_count": len(followers),
        "following_count": len(following),
        "followers": followers,
        "following": following,
    }

    if calculate_friends:
        friends = list(set(followers) & set(following))
        result["friends_count"] = len(friends)
        result["friends"] = friends

        if crawl_friends_detail_flag:
            result["friends_detail"] = await crawl_friends_detail(
                page,
                friends,
                delay_range,
                batch_size,
                batch_delay
            )

    return result