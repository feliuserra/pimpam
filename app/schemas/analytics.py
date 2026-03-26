from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_users: int
    total_posts: int
    total_comments: int
    total_communities: int
    active_users_7d: int


class TimeseriesPoint(BaseModel):
    date: str  # ISO date string YYYY-MM-DD
    count: int


class TopCommunity(BaseModel):
    name: str
    post_count: int
    member_count: int


class ModerationSummary(BaseModel):
    pending_reports: int
    bans_count: int
    removals_count: int
    suspensions_count: int
