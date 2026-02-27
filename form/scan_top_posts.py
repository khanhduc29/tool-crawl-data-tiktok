def get_scan_top_posts_form():
    return {
        "scan_type": "top_posts",

        "scan_account": "tool_bot_01",
        "keyword": "makeup",

        "sort_by": "view",        # view | like | comment
        "limit": 50,

        # chống ban
        "delay_range": (3000, 6000),
        "batch_size": 5,
        "batch_delay": 8000,

        # mức độ quét
        "deep_scan": False
    }