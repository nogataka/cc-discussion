"""
Codex History Reader
====================

Read Codex session history from ~/.codex/sessions/
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Codex session storage paths
CODEX_SESSIONS_ROOT = Path.home() / ".codex" / "sessions"
CODEX_HISTORY_FILE = Path.home() / ".codex" / "history.jsonl"


def list_codex_projects() -> list[dict]:
    """
    List all Codex projects (workspaces).

    Returns a list of projects, each with:
    - id: encoded workspace path
    - name: workspace directory name
    - path: full workspace path
    - last_modified_at: ISO timestamp
    - session_count: number of sessions
    """
    if not CODEX_SESSIONS_ROOT.exists():
        logger.warning(f"Codex sessions directory not found: {CODEX_SESSIONS_ROOT}")
        return []

    projects: dict[str, dict] = {}

    # Recursively find all .jsonl session files
    for jsonl_file in CODEX_SESSIONS_ROOT.rglob("*.jsonl"):
        try:
            session_meta = _read_session_header(jsonl_file)
            if not session_meta:
                continue

            workspace_path = session_meta.get("cwd", "")
            if not workspace_path:
                continue

            # Get file modification time
            file_mtime = datetime.fromtimestamp(jsonl_file.stat().st_mtime)

            if workspace_path not in projects:
                projects[workspace_path] = {
                    "id": _encode_path(workspace_path),
                    "name": Path(workspace_path).name,
                    "path": workspace_path,
                    "last_modified_at": file_mtime,
                    "session_count": 0,
                }

            projects[workspace_path]["session_count"] += 1
            if file_mtime > projects[workspace_path]["last_modified_at"]:
                projects[workspace_path]["last_modified_at"] = file_mtime

        except Exception as e:
            logger.warning(f"Error reading Codex session file {jsonl_file}: {e}")

    # Convert to list and format timestamps
    result = []
    for project in projects.values():
        project["last_modified_at"] = project["last_modified_at"].isoformat()
        result.append(project)

    # Sort by last modified (most recent first)
    result.sort(key=lambda p: p["last_modified_at"], reverse=True)
    return result


def list_codex_sessions(project_id: str) -> list[dict]:
    """
    List all sessions for a Codex project.

    Args:
        project_id: Encoded workspace path

    Returns a list of sessions, each with:
    - id: session file path (encoded)
    - session_uuid: unique session UUID
    - first_user_message: first user message in the session
    - message_count: total number of entries
    - last_modified_at: ISO timestamp
    """
    workspace_path = _decode_path(project_id)
    if not workspace_path:
        return []

    if not CODEX_SESSIONS_ROOT.exists():
        return []

    sessions = []

    for jsonl_file in CODEX_SESSIONS_ROOT.rglob("*.jsonl"):
        try:
            session_meta = _read_session_header(jsonl_file)
            if not session_meta:
                continue

            if session_meta.get("cwd") != workspace_path:
                continue

            # Count messages and get first user message
            message_count = 0
            first_user_message = None

            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        message_count += 1

                        # Look for first user message
                        if first_user_message is None:
                            if entry.get("type") == "response_item":
                                payload = entry.get("payload", {})
                                if payload.get("role") == "user":
                                    content = payload.get("content", "")
                                    if isinstance(content, str):
                                        first_user_message = content[:200]
                                    elif isinstance(content, list):
                                        for c in content:
                                            if isinstance(c, dict) and c.get("type") == "input_text":
                                                first_user_message = c.get("text", "")[:200]
                                                break
                            elif entry.get("type") == "event_msg":
                                payload = entry.get("payload", {})
                                if payload.get("type") == "user_message":
                                    first_user_message = payload.get("text", "")[:200]
                    except json.JSONDecodeError:
                        continue

            sessions.append({
                "id": _encode_path(str(jsonl_file)),
                "session_uuid": session_meta.get("id", ""),
                "jsonl_file_path": str(jsonl_file),
                "first_user_message": first_user_message,
                "message_count": message_count,
                "last_modified_at": datetime.fromtimestamp(jsonl_file.stat().st_mtime).isoformat(),
            })

        except Exception as e:
            logger.warning(f"Error reading Codex session file {jsonl_file}: {e}")

    # Sort by last modified (most recent first)
    sessions.sort(key=lambda s: s["last_modified_at"], reverse=True)
    return sessions


def get_codex_session_context(session_id: str, max_chars: int = 50000) -> str:
    """
    Get the conversation context from a Codex session.

    Args:
        session_id: Encoded session file path
        max_chars: Maximum characters to return

    Returns:
        Formatted conversation history string
    """
    file_path = _decode_path(session_id)
    if not file_path or not Path(file_path).exists():
        return ""

    try:
        lines = []
        with open(file_path, "r", encoding="utf-8") as f:
            for line_str in f:
                line_str = line_str.strip()
                if not line_str:
                    continue
                try:
                    entry = json.loads(line_str)
                    formatted = _format_codex_entry(entry)
                    if formatted:
                        lines.append(formatted)
                except json.JSONDecodeError:
                    continue

        context = "\n".join(lines)
        if len(context) > max_chars:
            context = context[-max_chars:]
            # Try to start at a message boundary
            newline_idx = context.find("\n[")
            if newline_idx > 0:
                context = context[newline_idx + 1:]

        return context

    except Exception as e:
        logger.error(f"Error reading Codex session context: {e}")
        return ""


def _read_session_header(jsonl_file: Path) -> Optional[dict]:
    """Read the session metadata from the first line of a Codex session file."""
    try:
        with open(jsonl_file, "r", encoding="utf-8") as f:
            first_line = f.readline().strip()
            if not first_line:
                return None

            entry = json.loads(first_line)
            if entry.get("type") == "session_meta":
                return entry.get("payload", {})

            # Some files might have the metadata in a different format
            if "cwd" in entry:
                return entry

            return None
    except Exception:
        return None


def _format_codex_entry(entry: dict) -> Optional[str]:
    """Format a Codex session entry for context injection."""
    entry_type = entry.get("type")

    if entry_type == "response_item":
        payload = entry.get("payload", {})
        role = payload.get("role")
        content = payload.get("content", "")

        if role == "user":
            if isinstance(content, str):
                return f"[User]: {content}"
            elif isinstance(content, list):
                texts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "input_text":
                        texts.append(c.get("text", ""))
                if texts:
                    return f"[User]: {' '.join(texts)}"

        elif role == "assistant":
            if isinstance(content, str):
                return f"[Assistant]: {content}"
            elif isinstance(content, list):
                texts = []
                for c in content:
                    if isinstance(c, dict) and c.get("type") == "output_text":
                        texts.append(c.get("text", ""))
                if texts:
                    return f"[Assistant]: {' '.join(texts)}"

        elif payload.get("type") == "function_call":
            name = payload.get("name", "unknown")
            return f"[Tool Call]: {name}"

    elif entry_type == "event_msg":
        payload = entry.get("payload", {})
        msg_type = payload.get("type")

        if msg_type == "user_message":
            return f"[User]: {payload.get('text', '')}"
        elif msg_type == "agent_message":
            return f"[Assistant]: {payload.get('text', '')}"

    return None


def _encode_path(path: str) -> str:
    """Encode a path to a URL-safe ID."""
    import base64
    return base64.urlsafe_b64encode(path.encode()).decode()


def _decode_path(encoded: str) -> Optional[str]:
    """Decode a path ID back to the original path."""
    try:
        import base64
        return base64.urlsafe_b64decode(encoded.encode()).decode()
    except Exception:
        return None
