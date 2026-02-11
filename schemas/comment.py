from pydantic import BaseModel

class TikTokComment(BaseModel):
    scan_account: str
    video_url: str

    comment_id: str
    comment_text: str

    user_id: str
    username: str
    display_name: str | None
    profile_url: str
    