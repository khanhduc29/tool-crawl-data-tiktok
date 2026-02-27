from dataclasses import dataclass
from typing import Optional


@dataclass
class TikTokPost:
    scan_account: str
    keyword: str

    video_id: str
    video_url: str
    caption: Optional[str]

    author_username: str
    author_profile: str

    view_count: Optional[int]
    like_count: Optional[int]
    comment_count: Optional[int]
    share_count: Optional[int]

    create_time: Optional[str]