from crawlers.scan_top_posts import crawl_top_posts
from crawlers.search_user import crawl_users_by_keyword
from crawlers.scan_relations import crawl_relations
from crawlers.scan_video_comments import crawl_video_comments


SCAN_DISPATCHER = {
    "top_posts": crawl_top_posts,
    "users": crawl_users_by_keyword,
    "relations": crawl_relations,
    "video_comments": crawl_video_comments,
}


async def dispatch_scan(scan_type: str, page, input_data: dict):
    if scan_type not in SCAN_DISPATCHER:
        raise ValueError(f"❌ Unsupported scan_type: {scan_type}")

    crawl_func = SCAN_DISPATCHER[scan_type]
    return await crawl_func(page=page, **input_data)