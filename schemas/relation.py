from pydantic import BaseModel

class TikTokRelation(BaseModel):
    scan_account: str
    source_username: str
    friend_type: str

    tiktok_id: str
    username: str
    display_name: str | None
    profile_url: str
