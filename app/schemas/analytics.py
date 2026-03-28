from datetime import datetime
from enum import Enum

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Existing schemas (unchanged)
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# New: time window enum (shared between CRUD and API)
# ---------------------------------------------------------------------------


class TimeWindow(str, Enum):
    HOUR = "1h"
    DAY = "24h"
    WEEK = "7d"
    MONTH = "30d"


# ---------------------------------------------------------------------------
# New: window-relative network health overview
# ---------------------------------------------------------------------------


class WindowOverviewStats(BaseModel):
    """Stat counts within an arbitrary time window."""

    active_users: int  # distinct post/comment authors in window
    new_users: int  # User.created_at >= cutoff
    new_posts: int  # Post.created_at >= cutoff
    new_messages: int  # Message.created_at >= cutoff
    window_label: str  # "1h" | "24h" | "7d" | "30d"


# ---------------------------------------------------------------------------
# New: sub-day granular timeseries
# ---------------------------------------------------------------------------


class GranularTimeseriesPoint(BaseModel):
    # ISO 8601: "2026-03-27T14:00:00+00:00" for hourly, "2026-03-27" for daily
    bucket: str
    count: int


# ---------------------------------------------------------------------------
# New: security metrics
# ---------------------------------------------------------------------------


class SuspiciousIpEntry(BaseModel):
    """Hashed IP (SHA-256) with its failure count. Never stores plaintext IPs."""

    ip_hash: str
    failure_count: int


class SecurityMetrics(BaseModel):
    window_label: str
    failed_logins: int
    successful_logins: int
    failure_rate: float  # 0.0–1.0
    password_reset_requests: int
    new_registrations: int
    suspicious_ips: list[SuspiciousIpEntry]


# ---------------------------------------------------------------------------
# New: security alerts
# ---------------------------------------------------------------------------


class SecurityAlert(BaseModel):
    alert_type: (
        str  # "high_failure_rate" | "login_failure_ratio" | "registration_spike"
    )
    message: str
    value: float  # measured value that triggered the alert
    threshold: float  # threshold that was breached


class SecurityAlertList(BaseModel):
    alerts: list[SecurityAlert]
    generated_at: datetime
