from pydantic import BaseModel

class TikTokUser(BaseModel):
    scan_account: str
    keyword: str | None

    tiktok_id: str
    username: str
    display_name: str | None
    bio: str | None
    avatar_url: str | None
    profile_url: str

    follower_count: int | None
    following_count: int | None
    video_count: int | None
