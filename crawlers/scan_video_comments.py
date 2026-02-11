import asyncio
import random


async def _random_delay(delay_range):
    await asyncio.sleep(random.uniform(*delay_range) / 1000)


# ==========================================================
# SCROLL COMMENT PANEL + EXTRACT FULL COMMENT DATA
# ==========================================================
async def _scroll_comments(page, limit, delay_range):
    print("🔎 Waiting for DivCommentMain...")

    await page.wait_for_selector('div[class*="DivCommentMain"]', timeout=20000)

    comment_main = await page.query_selector('div[class*="DivCommentMain"]')

    if not comment_main:
        print("❌ Cannot find DivCommentMain")
        return []

    print("✅ Found DivCommentMain")

    # Hover đúng panel comment
    box = await comment_main.bounding_box()
    await page.mouse.move(
        box["x"] + box["width"] / 2,
        box["y"] + box["height"] / 2
    )

    print("🖱 Hovered inside DivCommentMain")

    results = []
    last_count = 0
    stable_rounds = 0

    while len(results) < limit:

        blocks = await page.query_selector_all(
            'div[class*="DivCommentObjectWrapper"]'
        )

        print(f"👉 Blocks detected: {len(blocks)}")

        for block in blocks:

            # ===== PROFILE LINK =====
            link = await block.query_selector('a[href^="/@"]')
            href = await link.get_attribute("href") if link else None

            # ===== USERNAME DISPLAY =====
            username_el = await block.query_selector(
                '[data-e2e^="comment-username"] p'
            )
            username = await username_el.inner_text() if username_el else None

            # ===== COMMENT CONTENT =====
            content_el = await block.query_selector(
                '[data-e2e="comment-level-1"] span'
            )
            content = await content_el.inner_text() if content_el else None

            # ===== DATE =====
            date_el = await block.query_selector(
                'div[class*="DivCommentSubContentWrapper"] span'
            )
            date = await date_el.inner_text() if date_el else None

            # ===== LIKE COUNT =====
            like_el = await block.query_selector(
                'div[class*="DivLikeContainer"] span'
            )
            likes = await like_el.inner_text() if like_el else "0"

            if href:
                full_url = "https://www.tiktok.com" + href

                comment_data = {
                    "profile_url": full_url,
                    "display_name": username,
                    "comment": content,
                    "date": date,
                    "likes": likes
                }

                if comment_data not in results:
                    results.append(comment_data)

        print(f"💬 Total comments collected: {len(results)}")

        # Scroll đúng panel, KHÔNG scroll page
        await page.evaluate(
            "(el) => el.scrollBy(0, 1000)",
            comment_main
        )

        await asyncio.sleep(2)

        if len(results) == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= 4:
            print("🛑 No more comments loading → break")
            break

        last_count = len(results)

    return results[:limit]


# ==========================================================
# MAIN CRAWLER
# ==========================================================
async def crawl_video_comments(
    page,
    video_url,
    limit_comments,
    delay_range,
    batch_size,
    batch_delay,
    deep_scan_profile=False,
    **kwargs
):
    print("\n===== ENTER crawl_video_comments =====")
    print(f"🎬 Video URL: {video_url}")

    await page.goto(video_url)
    await page.wait_for_timeout(5000)

    # ==============================
    # CLOSE KEYBOARD POPUP IF EXISTS
    # ==============================
    popup_close = await page.query_selector(
        'div[class*="DivKeyboardShortcutContainer"] svg'
    )

    if popup_close:
        print("✅ Closing keyboard popup")
        await popup_close.click()
        await page.wait_for_timeout(1000)

    # ==============================
    # CLICK COMMENT ICON
    # ==============================
    print("🔎 Finding comment icon...")

    comment_icon = await page.query_selector('[data-e2e="comment-icon"]')

    if not comment_icon:
        print("❌ Cannot find comment icon")
        await page.pause()
        return []

    box = await comment_icon.bounding_box()
    await page.mouse.move(
        box["x"] + box["width"] / 2,
        box["y"] + box["height"] / 2
    )

    print("➡️ Clicking comment icon")
    await comment_icon.click()

    await page.wait_for_timeout(3000)

    # ==============================
    # SCROLL & EXTRACT
    # ==============================
    comment_data = await _scroll_comments(
        page,
        limit_comments,
        delay_range
    )

    print(f"✅ Scroll returned {len(comment_data)} comments")
    print("===== EXIT crawl_video_comments =====\n")

    return comment_data
