import asyncio
import random


async def _random_delay(delay_range):
    await asyncio.sleep(random.uniform(*delay_range) / 1000)


async def _get_scroll_container(page):
    return await page.evaluate_handle("""
        () => {
            const modal = document.querySelector('[data-e2e="follow-info-popup"]');
            if (!modal) return null;

            const elements = modal.querySelectorAll('*');

            for (const el of elements) {
                const style = window.getComputedStyle(el);
                if (
                    (style.overflowY === 'auto' || style.overflowY === 'scroll') &&
                    el.scrollHeight > el.clientHeight
                ) {
                    return el;
                }
            }
            return null;
        }
    """)


async def _scroll_until_limit(page, limit, delay_range):
    users = set()

    print("🔎 Waiting for list container...")

    await page.wait_for_selector('[data-e2e="follow-info-popup"]')

    # Lấy container theo prefix class
    scroll_container = await page.query_selector(
        '[data-e2e="follow-info-popup"] div[class*="DivUserListContainer"]'
    )

    if not scroll_container:
        print("❌ Không tìm thấy DivUserListContainer")
        return []

    # Hover vào container
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

        # Scroll nhỏ liên tục thay vì 1 phát lớn
        for _ in range(5):
            await page.mouse.wheel(0, 300)
            await asyncio.sleep(0.2)

        # Đợi load network
        await asyncio.sleep(4)

        if len(users) == last_count:
            no_change_rounds += 1
            print(f"⚠ No change round: {no_change_rounds}")
        else:
            no_change_rounds = 0

        if no_change_rounds >= 3:
            print("🛑 Không load thêm sau nhiều lần thử → break")
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
        print("❌ Không tìm thấy followers button")
        return []

    await btn.click()

    await page.wait_for_selector('[data-e2e="follow-info-popup"]')

    # Click tab Followers bên trong modal bằng title
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
        print("❌ Không tìm thấy following button")
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
    **kwargs
):
    followers = await crawl_followers(
        page,
        target_username,
        followers_limit,
        delay_range
    )

    await asyncio.sleep(batch_delay / 1000)

    following = await crawl_following(
        page,
        target_username,
        following_limit,
        delay_range
    )

    result = {
        "username": target_username,
        "followers_count": len(followers),
        "following_count": len(following),
        "followers": followers,
        "following": following
    }

    if calculate_friends:
        friends = list(set(followers) & set(following))
        result["friends_count"] = len(friends)
        result["friends"] = friends

    return result
