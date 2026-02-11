def get_scan_relations_form():
    return {
        "scan_type": "relations",

        "scan_account": "tool_bot_01",
        "keyword": "makeup",

        "source_username": "flowerknowsglobal",
        "relation_type": "following",   # following | follower
        "limit": 50,

        # chống ban
        "delay_range": (3000, 6000),
        "batch_size": 10,
        "batch_delay": 12000,

        # mức độ quét
        "deep_scan": False,             # True = vào profile từng người
    }
