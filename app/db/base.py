# This file is imported by Alembic's env.py so it can discover all models.
# Add every new model module here.
from app.db.base_class import Base  # noqa: F401
from app.models.admin import (  # noqa: F401
    AdminContentRemoval,
    GlobalBan,
    UserSuspension,
)
from app.models.block import Block  # noqa: F401
from app.models.comment import Comment, CommentReaction  # noqa: F401
from app.models.community import Community, CommunityMember  # noqa: F401
from app.models.community_audit import CommunityAuditLog  # noqa: F401
from app.models.community_karma import CommunityKarma  # noqa: F401
from app.models.community_label import CommunityLabel  # noqa: F401
from app.models.consent import ConsentLog  # noqa: F401
from app.models.curated_pick import CuratedPick  # noqa: F401
from app.models.device_token import DeviceToken  # noqa: F401
from app.models.follow import Follow  # noqa: F401
from app.models.friend_group import FriendGroup, FriendGroupMember  # noqa: F401
from app.models.hashtag import Hashtag, PostHashtag  # noqa: F401
from app.models.hashtag_subscription import HashtagSubscription  # noqa: F401
from app.models.issue import Issue, IssueComment, IssueVote  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.notification import Notification, NotificationPreference  # noqa: F401
from app.models.password_reset import PasswordResetToken  # noqa: F401
from app.models.post import Post  # noqa: F401
from app.models.post_image import PostImage  # noqa: F401
from app.models.remote_actor import RemoteActor  # noqa: F401
from app.models.report import Report  # noqa: F401
from app.models.story import Story  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.vote import Vote  # noqa: F401
