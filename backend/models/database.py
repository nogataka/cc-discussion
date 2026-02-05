"""
Database Models
===============

SQLite database schema for discussion rooms using SQLAlchemy.
"""

import enum
from datetime import datetime, timezone
from pathlib import Path
from typing import Generator

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker
from sqlalchemy.types import JSON


def _utc_now() -> datetime:
    """Return current UTC time."""
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    """SQLAlchemy 2.0 style declarative base."""
    pass


class RoomStatus(enum.Enum):
    """Status of a discussion room."""
    WAITING = "waiting"      # Room created, waiting for discussion to start
    ACTIVE = "active"        # Discussion in progress
    PAUSED = "paused"        # Discussion paused
    COMPLETED = "completed"  # Discussion ended


class MeetingType(enum.Enum):
    """会議タイプ"""
    PROGRESS_CHECK = "progress_check"      # 1. 進捗・状況確認
    SPEC_ALIGNMENT = "spec_alignment"      # 2. 要件・仕様の認識合わせ
    TECHNICAL_REVIEW = "technical_review"  # 3. 技術検討・設計判断
    ISSUE_RESOLUTION = "issue_resolution"  # 4. 課題・不具合対応
    REVIEW = "review"                      # 5. レビュー
    PLANNING = "planning"                  # 6. 計画・タスク整理
    RELEASE_OPS = "release_ops"            # 7. リリース・運用判断
    RETROSPECTIVE = "retrospective"        # 8. 改善・振り返り
    OTHER = "other"                        # 9. その他（カスタム）


class AgentType(enum.Enum):
    """エージェントタイプ"""
    CLAUDE = "claude"
    CODEX = "codex"


class DiscussionRoom(Base):
    """A discussion room where multiple Claudes converse."""
    __tablename__ = "discussion_rooms"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    topic = Column(Text, nullable=True)
    status = Column(
        Enum(RoomStatus, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=RoomStatus.WAITING
    )
    max_turns = Column(Integer, default=20)
    current_turn = Column(Integer, default=0)
    created_at = Column(DateTime, default=_utc_now)
    updated_at = Column(DateTime, default=_utc_now, onupdate=_utc_now)

    # Meeting type settings
    meeting_type = Column(
        Enum(MeetingType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=MeetingType.TECHNICAL_REVIEW
    )
    custom_meeting_description = Column(Text, nullable=True)  # "その他"選択時のカスタム説明
    language = Column(String(10), default="ja")

    participants = relationship(
        "RoomParticipant",
        back_populates="room",
        cascade="all, delete-orphan"
    )
    messages = relationship(
        "DiscussionMessage",
        back_populates="room",
        cascade="all, delete-orphan"
    )

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "name": self.name,
            "topic": self.topic,
            "status": self.status.value if self.status else "waiting",
            "max_turns": self.max_turns,
            "current_turn": self.current_turn,
            "meeting_type": self.meeting_type.value if self.meeting_type else "technical_review",
            "custom_meeting_description": self.custom_meeting_description,
            "language": self.language or "ja",
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "participant_count": len(self.participants) if self.participants else 0,
        }


class RoomParticipant(Base):
    """A Claude participant in a discussion room."""
    __tablename__ = "room_participants"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("discussion_rooms.id"), nullable=False, index=True)

    # Participant identity
    name = Column(String(50), nullable=False)
    role = Column(String(100), nullable=True)
    color = Column(String(7), default="#6366f1")

    # Context injection from ClaudeCode history
    context_project_dir = Column(String(500), nullable=True)
    context_session_id = Column(String(100), nullable=True)
    context_summary = Column(Text, nullable=True)

    # State
    is_speaking = Column(Boolean, default=False)
    message_count = Column(Integer, default=0)

    # Agent settings
    is_facilitator = Column(Boolean, default=False)
    agent_type = Column(
        Enum(AgentType, native_enum=False, values_callable=lambda x: [e.value for e in x]),
        default=AgentType.CLAUDE
    )

    room = relationship("DiscussionRoom", back_populates="participants")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "name": self.name,
            "role": self.role,
            "color": self.color,
            "context_project_dir": self.context_project_dir,
            "context_session_id": self.context_session_id,
            "has_context": bool(self.context_session_id),
            "is_speaking": self.is_speaking,
            "message_count": self.message_count,
            "is_facilitator": self.is_facilitator or False,
            "agent_type": self.agent_type.value if self.agent_type else "claude",
        }


class DiscussionMessage(Base):
    """A message in the discussion."""
    __tablename__ = "discussion_messages"

    id = Column(Integer, primary_key=True, index=True)
    room_id = Column(Integer, ForeignKey("discussion_rooms.id"), nullable=False, index=True)
    participant_id = Column(Integer, ForeignKey("room_participants.id"), nullable=True)

    role = Column(String(20), nullable=False)  # "system" | "participant" | "moderator"
    content = Column(Text, nullable=False)
    extra_data = Column(JSON, nullable=True)  # Tool calls, thinking, etc.

    turn_number = Column(Integer, nullable=False)
    created_at = Column(DateTime, default=_utc_now)

    room = relationship("DiscussionRoom", back_populates="messages")

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "room_id": self.room_id,
            "participant_id": self.participant_id,
            "role": self.role,
            "content": self.content,
            "extra_data": self.extra_data,
            "turn_number": self.turn_number,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


# Database setup
DATABASE_PATH = Path(__file__).parent.parent.parent / "discussion.db"


def get_database_url() -> str:
    """Return the SQLAlchemy database URL."""
    return f"sqlite:///{DATABASE_PATH.as_posix()}"


_engine = None
_session_maker = None


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        _engine = create_engine(
            get_database_url(),
            connect_args={"check_same_thread": False}
        )
        Base.metadata.create_all(bind=_engine)
    return _engine


def get_session_maker():
    """Get or create the session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine()
        )
    return _session_maker


def get_db() -> Generator[Session, None, None]:
    """Dependency for FastAPI to get database session."""
    SessionLocal = get_session_maker()
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
