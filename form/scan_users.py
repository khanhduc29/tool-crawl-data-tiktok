def get_scan_users_form():
    return {
        # ==== THÔNG TIN QUÉT ====
        "scan_type": "search_users",

        "scan_account": "tool_bot_01",
        "keyword": "makeup",
        "limit": 20,

        # ==== CHỐNG BAN ====
        "delay_range": (2500, 5000),   # ms
        "batch_size": 5,
        "batch_delay": 8000,           # ms

        # ==== MỨC ĐỘ QUÉT ====
        "deep_scan": True,             # True = vào profile
        "scan_relations": False,
        "scan_comments": False,
    }
