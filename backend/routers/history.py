"""
History Router
==============

API endpoints for browsing ClaudeCode conversation history.
"""

from typing import Any, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.history_reader import (
    list_projects,
    list_sessions,
    load_session_history,
    decode_session_id,
)
from ..services.codex_history_reader import (
    list_codex_projects,
    list_codex_sessions,
)

router = APIRouter(prefix="/api/history", tags=["history"])


class ProjectResponse(BaseModel):
    """Response model for a project."""
    id: str
    name: str
    path: str
    last_modified_at: str


class SessionResponse(BaseModel):
    """Response model for a session."""
    id: str
    jsonl_file_path: str
    last_modified_at: str
    message_count: int
    first_user_message: Optional[str]


class ToolCall(BaseModel):
    """Tool call model."""
    id: Optional[str]
    name: Optional[str]
    input: dict


class ToolResult(BaseModel):
    """Tool result model."""
    tool_use_id: Optional[str]
    content: Any
    is_error: bool = False


class ConversationResponse(BaseModel):
    """Response model for a conversation message."""
    type: str
    uuid: str
    timestamp: str
    content: Any
    is_sidechain: bool
    parent_uuid: Optional[str]
    tool_calls: List[ToolCall]
    tool_results: List[ToolResult]


class SessionDetailResponse(BaseModel):
    """Response model for session detail."""
    id: str
    jsonl_file_path: str
    conversations: List[ConversationResponse]


@router.get("/projects", response_model=List[ProjectResponse])
async def get_claude_projects():
    """List all ClaudeCode projects with history."""
    projects = list_projects()
    return [
        ProjectResponse(
            id=p.id,
            name=p.name,
            path=p.path,
            last_modified_at=p.last_modified_at.isoformat(),
        )
        for p in projects
    ]


@router.get("/projects/{project_id}/sessions", response_model=List[SessionResponse])
async def get_project_sessions(project_id: str, limit: int = 50):
    """Get all sessions for a project."""
    sessions = list_sessions(project_id, limit=limit)
    return [
        SessionResponse(
            id=s.id,
            jsonl_file_path=s.jsonl_file_path,
            last_modified_at=s.last_modified_at.isoformat(),
            message_count=s.message_count,
            first_user_message=s.first_user_message,
        )
        for s in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionDetailResponse)
async def get_session_detail(session_id: str):
    """Get full session detail with all conversations."""
    try:
        messages = load_session_history(session_id)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionDetailResponse(
        id=session_id,
        jsonl_file_path=decode_session_id(session_id),
        conversations=[
            ConversationResponse(
                type=m.type,
                uuid=m.uuid,
                timestamp=m.timestamp,
                content=m.content,
                is_sidechain=m.is_sidechain,
                parent_uuid=m.parent_uuid,
                tool_calls=[
                    ToolCall(
                        id=tc.get('id'),
                        name=tc.get('name'),
                        input=tc.get('input', {}),
                    )
                    for tc in m.tool_calls
                ],
                tool_results=[
                    ToolResult(
                        tool_use_id=tr.get('tool_use_id'),
                        content=tr.get('content'),
                        is_error=tr.get('is_error', False),
                    )
                    for tr in m.tool_results
                ],
            )
            for m in messages
        ],
    )


# ============================================
# Codex History Endpoints
# ============================================

class CodexProjectResponse(BaseModel):
    """Response model for a Codex project."""
    id: str
    name: str
    path: str
    last_modified_at: str
    session_count: int


class CodexSessionResponse(BaseModel):
    """Response model for a Codex session."""
    id: str
    session_uuid: str
    jsonl_file_path: str
    first_user_message: Optional[str]
    message_count: int
    last_modified_at: str


@router.get("/codex/projects", response_model=List[CodexProjectResponse])
async def get_codex_projects():
    """List all Codex projects with history."""
    projects = list_codex_projects()
    return [
        CodexProjectResponse(
            id=p["id"],
            name=p["name"],
            path=p["path"],
            last_modified_at=p["last_modified_at"],
            session_count=p["session_count"],
        )
        for p in projects
    ]


@router.get("/codex/projects/{project_id}/sessions", response_model=List[CodexSessionResponse])
async def get_codex_project_sessions(project_id: str):
    """Get all sessions for a Codex project."""
    sessions = list_codex_sessions(project_id)
    return [
        CodexSessionResponse(
            id=s["id"],
            session_uuid=s["session_uuid"],
            jsonl_file_path=s["jsonl_file_path"],
            first_user_message=s["first_user_message"],
            message_count=s["message_count"],
            last_modified_at=s["last_modified_at"],
        )
        for s in sessions
    ]
