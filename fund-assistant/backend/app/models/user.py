from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, DateTime, JSON, Boolean
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(120), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)

    # AI model API keys: {"openai": "sk-xxx", "deepseek": "sk-xxx", "claude": "sk-ant-xxx"}
    api_keys = Column(JSON, default=dict)

    # Notification configs: {"email": {"address": "..."}, "feishu": {"webhook": "..."}, ...}
    notify_configs = Column(JSON, default=dict)

    # Preferences: {"theme": "dark", "default_ai_model": "deepseek", ...}
    preferences = Column(JSON, default=dict)

    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
