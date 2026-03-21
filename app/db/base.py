# This file is imported by Alembic's env.py so it can discover all models.
# Add every new model module here.
from app.db.base_class import Base  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.post import Post  # noqa: F401
from app.models.community import Community, CommunityMember  # noqa: F401
from app.models.message import Message  # noqa: F401
from app.models.follow import Follow  # noqa: F401
from app.models.remote_actor import RemoteActor  # noqa: F401
