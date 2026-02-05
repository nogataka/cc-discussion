"""
Rooms Router
============

API endpoints for managing discussion rooms.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from pathlib import Path

from ..models.database import (
    DiscussionRoom,
    RoomParticipant,
    DiscussionMessage,
    RoomStatus,
    MeetingType,
    AgentType,
    get_db,
)
from ..services.history_reader import decode_project_id, get_original_path_from_dir
from ..services.codex_history_reader import _decode_path as decode_codex_path

router = APIRouter(prefix="/api/rooms", tags=["rooms"])


def get_project_name(participant: RoomParticipant) -> Optional[str]:
    """Get project name from participant's context_project_dir."""
    if not participant.context_project_dir:
        return None

    try:
        agent_type = participant.agent_type.value if participant.agent_type else "claude"

        if agent_type == "codex":
            # Codex: context_project_dir is base64-encoded path
            actual_path = decode_codex_path(participant.context_project_dir)
            if actual_path:
                return Path(actual_path).name
        else:
            # Claude: context_project_dir is encoded project ID
            internal_dir = Path(decode_project_id(participant.context_project_dir))
            actual_path = get_original_path_from_dir(internal_dir)
            if actual_path:
                return Path(actual_path).name
    except Exception:
        pass

    return None


# Request/Response Models

class ParticipantCreate(BaseModel):
    """Request model for creating a participant."""
    name: str = Field(..., min_length=1, max_length=50)
    role: Optional[str] = Field(None, max_length=100)
    color: str = Field(default="#6366f1", pattern=r"^#[0-9a-fA-F]{6}$")
    context_project_dir: Optional[str] = None
    context_session_id: Optional[str] = None
    is_facilitator: bool = False
    agent_type: str = Field(default="claude", pattern=r"^(claude|codex)$")


class RoomCreate(BaseModel):
    """Request model for creating a room."""
    name: str = Field(..., min_length=1, max_length=200)
    topic: Optional[str] = None
    max_turns: int = Field(default=20, ge=1, le=100)
    meeting_type: str = Field(default="technical_review")
    custom_meeting_description: Optional[str] = None  # "その他"選択時のカスタム説明
    language: str = Field(default="ja", pattern=r"^(ja|en)$")
    participants: List[ParticipantCreate] = Field(..., min_length=2, max_length=3)


class ModeratorMessage(BaseModel):
    """Request model for moderator intervention."""
    content: str = Field(..., min_length=1)


class RoomResponse(BaseModel):
    """Response model for a room."""
    id: int
    name: str
    topic: Optional[str]
    status: str
    current_turn: int
    max_turns: int
    meeting_type: str
    custom_meeting_description: Optional[str]
    language: str
    participant_count: int
    created_at: str


class ParticipantResponse(BaseModel):
    """Response model for a participant."""
    id: int
    name: str
    role: Optional[str]
    color: str
    has_context: bool
    is_speaking: bool
    message_count: int
    is_facilitator: bool
    agent_type: str
    project_name: Optional[str] = None


class MessageResponse(BaseModel):
    """Response model for a message."""
    id: int
    participant_id: Optional[int]
    role: str
    content: str
    turn_number: int
    created_at: str


class RoomDetailResponse(BaseModel):
    """Detailed response model for a room."""
    id: int
    name: str
    topic: Optional[str]
    status: str
    current_turn: int
    max_turns: int
    meeting_type: str
    custom_meeting_description: Optional[str]
    language: str
    created_at: str
    participants: List[ParticipantResponse]
    messages: List[MessageResponse]


# Endpoints

@router.post("", response_model=RoomResponse)
async def create_room(room_data: RoomCreate, db: Session = Depends(get_db)):
    """Create a new discussion room with participants."""
    # Validate participant count
    if len(room_data.participants) < 2 or len(room_data.participants) > 3:
        raise HTTPException(
            status_code=400,
            detail="Rooms must have 2-3 participants"
        )

    # Parse meeting_type
    try:
        meeting_type_enum = MeetingType(room_data.meeting_type)
    except ValueError:
        meeting_type_enum = MeetingType.TECHNICAL_REVIEW

    # Create room
    room = DiscussionRoom(
        name=room_data.name,
        topic=room_data.topic,
        max_turns=room_data.max_turns,
        meeting_type=meeting_type_enum,
        custom_meeting_description=room_data.custom_meeting_description,
        language=room_data.language,
    )
    db.add(room)
    db.flush()

    # Create participants
    for p_data in room_data.participants:
        # Parse agent_type
        try:
            agent_type_enum = AgentType(p_data.agent_type)
        except ValueError:
            agent_type_enum = AgentType.CLAUDE

        participant = RoomParticipant(
            room_id=room.id,
            name=p_data.name,
            role=p_data.role,
            color=p_data.color,
            context_project_dir=p_data.context_project_dir,
            context_session_id=p_data.context_session_id,
            is_facilitator=p_data.is_facilitator,
            agent_type=agent_type_enum,
        )
        db.add(participant)

    db.commit()
    db.refresh(room)

    return RoomResponse(
        id=room.id,
        name=room.name,
        topic=room.topic,
        status=room.status.value,
        current_turn=room.current_turn,
        max_turns=room.max_turns,
        meeting_type=room.meeting_type.value if room.meeting_type else "technical_review",
        custom_meeting_description=room.custom_meeting_description,
        language=room.language or "ja",
        participant_count=len(room.participants),
        created_at=room.created_at.isoformat(),
    )


@router.get("", response_model=List[RoomResponse])
async def list_rooms(db: Session = Depends(get_db)):
    """List all discussion rooms."""
    rooms = db.query(DiscussionRoom).order_by(
        DiscussionRoom.created_at.desc()
    ).all()

    return [
        RoomResponse(
            id=r.id,
            name=r.name,
            topic=r.topic,
            status=r.status.value,
            current_turn=r.current_turn,
            max_turns=r.max_turns,
            meeting_type=r.meeting_type.value if r.meeting_type else "technical_review",
            custom_meeting_description=r.custom_meeting_description,
            language=r.language or "ja",
            participant_count=len(r.participants),
            created_at=r.created_at.isoformat(),
        )
        for r in rooms
    ]


@router.get("/{room_id}", response_model=RoomDetailResponse)
async def get_room(room_id: int, db: Session = Depends(get_db)):
    """Get room details including participants and messages."""
    room = db.query(DiscussionRoom).options(
        joinedload(DiscussionRoom.participants),
        joinedload(DiscussionRoom.messages)
    ).filter(
        DiscussionRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    return RoomDetailResponse(
        id=room.id,
        name=room.name,
        topic=room.topic,
        status=room.status.value,
        current_turn=room.current_turn,
        max_turns=room.max_turns,
        meeting_type=room.meeting_type.value if room.meeting_type else "technical_review",
        custom_meeting_description=room.custom_meeting_description,
        language=room.language or "ja",
        created_at=room.created_at.isoformat(),
        participants=[
            ParticipantResponse(
                id=p.id,
                name=p.name,
                role=p.role,
                color=p.color,
                has_context=bool(p.context_session_id),
                is_speaking=p.is_speaking,
                message_count=p.message_count,
                is_facilitator=p.is_facilitator or False,
                agent_type=p.agent_type.value if p.agent_type else "claude",
                project_name=get_project_name(p),
            )
            for p in room.participants
        ],
        messages=[
            MessageResponse(
                id=m.id,
                participant_id=m.participant_id,
                role=m.role,
                content=m.content,
                turn_number=m.turn_number,
                created_at=m.created_at.isoformat(),
            )
            for m in sorted(room.messages, key=lambda x: x.created_at)
        ],
    )


@router.delete("/{room_id}")
async def delete_room(room_id: int, db: Session = Depends(get_db)):
    """Delete a discussion room."""
    room = db.query(DiscussionRoom).filter(
        DiscussionRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    db.delete(room)
    db.commit()

    return {"status": "deleted", "room_id": room_id}


@router.post("/{room_id}/start")
async def start_discussion(room_id: int, db: Session = Depends(get_db)):
    """Start or resume a discussion."""
    room = db.query(DiscussionRoom).filter(
        DiscussionRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status == RoomStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Discussion already active")

    if room.status == RoomStatus.COMPLETED:
        raise HTTPException(status_code=400, detail="Discussion already completed")

    return {
        "status": "ready",
        "room_id": room_id,
        "websocket_url": f"/ws/rooms/{room_id}"
    }


@router.post("/{room_id}/pause")
async def pause_discussion(room_id: int, db: Session = Depends(get_db)):
    """Pause an active discussion."""
    room = db.query(DiscussionRoom).filter(
        DiscussionRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    if room.status != RoomStatus.ACTIVE:
        raise HTTPException(status_code=400, detail="Discussion not active")

    room.status = RoomStatus.PAUSED
    db.commit()

    return {"status": "paused", "room_id": room_id}


@router.post("/{room_id}/moderate")
async def add_moderator_message(
    room_id: int,
    message: ModeratorMessage,
    db: Session = Depends(get_db)
):
    """Add a moderator message to the discussion."""
    room = db.query(DiscussionRoom).filter(
        DiscussionRoom.id == room_id
    ).first()

    if not room:
        raise HTTPException(status_code=404, detail="Room not found")

    # Create moderator message
    msg = DiscussionMessage(
        room_id=room_id,
        participant_id=None,
        role="moderator",
        content=message.content,
        turn_number=room.current_turn,
    )
    db.add(msg)
    db.commit()
    db.refresh(msg)

    return MessageResponse(
        id=msg.id,
        participant_id=msg.participant_id,
        role=msg.role,
        content=msg.content,
        turn_number=msg.turn_number,
        created_at=msg.created_at.isoformat(),
    )
