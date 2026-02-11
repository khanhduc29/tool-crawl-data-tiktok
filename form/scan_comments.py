def get_scan_comments_form():
    return {
        "scan_type": "video_comments",

        "scan_account": "tool_bot_01",
        "keyword": "makeup",

        "video_url": "https://www.tiktok.com/@abc/video/123456",
        "limit": 200,

        "delay_range": (2000, 4000),
        "batch_size": 20,
        "batch_delay": 10000,

        "detect_intent": True,   # suy luận ý định
    }
