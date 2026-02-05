"""
ClaudeCode History Reader
=========================

Reads and parses ClaudeCode conversation history from ~/.claude/projects/
Based on claude-code-viewer-1 implementation - reads .jsonl files directly.
"""

import base64
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, List, Optional

CLAUDE_DIR = Path.home() / ".claude"
PROJECTS_DIR = CLAUDE_DIR / "projects"


def encode_project_id(path: str) -> str:
    """Encode a project path to a URL-safe base64 ID."""
    return base64.urlsafe_b64encode(path.encode('utf-8')).decode('ascii')


def decode_project_id(project_id: str) -> str:
    """Decode a project ID back to a path."""
    # Add padding if needed
    padding = 4 - len(project_id) % 4
    if padding != 4:
        project_id += '=' * padding
    return base64.urlsafe_b64decode(project_id.encode('ascii')).decode('utf-8')


def encode_session_id(jsonl_path: str) -> str:
    """Encode a session jsonl path to a URL-safe base64 ID."""
    return base64.urlsafe_b64encode(jsonl_path.encode('utf-8')).decode('ascii')


def decode_session_id(session_id: str) -> str:
    """Decode a session ID back to a jsonl path."""
    # Add padding if needed
    padding = 4 - len(session_id) % 4
    if padding != 4:
        session_id += '=' * padding
    return base64.urlsafe_b64decode(session_id.encode('ascii')).decode('utf-8')


@dataclass
class ProjectInfo:
    """Information about a ClaudeCode project."""
    id: str
    name: str
    path: str
    last_modified_at: datetime


@dataclass
class SessionInfo:
    """Information about a ClaudeCode session."""
    id: str
    jsonl_file_path: str
    last_modified_at: datetime
    message_count: int = 0
    first_user_message: Optional[str] = None


@dataclass
class ConversationMessage:
    """A message from a ClaudeCode conversation."""
    type: str  # "user" | "assistant" | "system" | "summary" | etc.
    uuid: str
    timestamp: str
    content: Any  # Can be string or structured content
    is_sidechain: bool = False
    parent_uuid: Optional[str] = None
    tool_calls: List[dict] = field(default_factory=list)
    tool_results: List[dict] = field(default_factory=list)
    raw_entry: dict = field(default_factory=dict)


def is_regular_session_file(filename: str) -> bool:
    """Check if file is a regular session file (not agent-*.jsonl)."""
    if not filename.endswith('.jsonl'):
        return False
    if filename.startswith('agent-'):
        return False
    return True


def extract_cwd_from_jsonl(jsonl_path: Path) -> Optional[str]:
    """
    Extract the cwd (current working directory) from a JSONL session file.
    This gives us the actual project path.
    Based on claude-code-viewer-1's ProjectMetaService implementation.
    """
    try:
        with open(jsonl_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    # Look for cwd field in the conversation entry
                    if isinstance(data, dict) and 'cwd' in data:
                        cwd = data['cwd']
                        if cwd:
                            return cwd
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass
    return None


def get_project_path_from_sessions(dir_entry: Path) -> Optional[str]:
    """
    Get the original project path by reading cwd from session JSONL files.
    This is the approach used by claude-code-viewer-1.
    """
    # Find all .jsonl files (excluding agent-*.jsonl)
    jsonl_files = []
    try:
        for f in dir_entry.iterdir():
            if f.is_file() and is_regular_session_file(f.name):
                try:
                    stat = f.stat()
                    jsonl_files.append((f, stat.st_mtime))
                except OSError:
                    continue
    except (IOError, OSError):
        return None

    # Sort by modification time (oldest first, to find original cwd)
    jsonl_files.sort(key=lambda x: x[1])

    # Try each file until we find a cwd
    for jsonl_path, _ in jsonl_files:
        cwd = extract_cwd_from_jsonl(jsonl_path)
        if cwd:
            return cwd

    return None


def get_original_path_from_dir(dir_entry: Path) -> str:
    """
    Get original project path from directory.
    Priority:
    1. sessions-index.json (if exists and has originalPath)
    2. cwd from .jsonl session files (like claude-code-viewer-1)
    3. Directory name as fallback
    """
    # Try to read from sessions-index.json first
    index_path = dir_entry / "sessions-index.json"
    if index_path.exists():
        try:
            with open(index_path, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
                original_path = index_data.get("originalPath", "")
                if original_path:
                    return original_path
        except (json.JSONDecodeError, IOError):
            pass

    # Try to extract cwd from session files (like claude-code-viewer-1)
    cwd = get_project_path_from_sessions(dir_entry)
    if cwd:
        return cwd

    # Fallback: just use directory name (don't try to decode - it's lossy)
    return dir_entry.name


def list_projects() -> List[ProjectInfo]:
    """List all ClaudeCode projects."""
    if not PROJECTS_DIR.exists():
        return []

    projects = []

    for dir_entry in PROJECTS_DIR.iterdir():
        if not dir_entry.is_dir() or dir_entry.name.startswith('.'):
            continue

        try:
            stat = dir_entry.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            last_modified = datetime.now()

        original_path = get_original_path_from_dir(dir_entry)
        project_name = original_path.split('/')[-1] if '/' in original_path else original_path

        projects.append(ProjectInfo(
            id=encode_project_id(str(dir_entry)),
            name=project_name,
            path=original_path,
            last_modified_at=last_modified,
        ))

    # Sort by last modified (newest first)
    return sorted(projects, key=lambda p: p.last_modified_at, reverse=True)


def list_sessions(project_id: str, limit: int = 50) -> List[SessionInfo]:
    """List all sessions for a project."""
    project_path = Path(decode_project_id(project_id))

    if not project_path.exists() or not project_path.is_dir():
        return []

    sessions = []

    for entry in project_path.iterdir():
        if not is_regular_session_file(entry.name):
            continue

        try:
            stat = entry.stat()
            last_modified = datetime.fromtimestamp(stat.st_mtime)
        except OSError:
            last_modified = datetime.now()

        # Get first user message and message count by scanning the file
        first_user_message = None
        message_count = 0

        try:
            with open(entry, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        msg_type = data.get('type')
                        if msg_type in ('user', 'assistant'):
                            message_count += 1
                        if msg_type == 'user' and first_user_message is None:
                            message = data.get('message', {})
                            content = message.get('content', '')
                            if isinstance(content, str):
                                first_user_message = content[:300]
                            elif isinstance(content, list):
                                # Find first text content
                                for item in content:
                                    if isinstance(item, str):
                                        first_user_message = item[:300]
                                        break
                                    elif isinstance(item, dict) and item.get('type') == 'text':
                                        first_user_message = item.get('text', '')[:300]
                                        break
                    except json.JSONDecodeError:
                        continue
        except IOError:
            pass

        sessions.append(SessionInfo(
            id=encode_session_id(str(entry)),
            jsonl_file_path=str(entry),
            last_modified_at=last_modified,
            message_count=message_count,
            first_user_message=first_user_message,
        ))

    # Sort by last modified (newest first)
    sessions = sorted(sessions, key=lambda s: s.last_modified_at, reverse=True)

    return sessions[:limit]


def parse_jsonl_entry(entry: dict) -> Optional[ConversationMessage]:
    """Parse a JSONL entry into a ConversationMessage."""
    entry_type = entry.get('type')
    if entry_type not in ('user', 'assistant', 'system', 'summary'):
        return None

    uuid = entry.get('uuid', '')
    timestamp = entry.get('timestamp', '')
    is_sidechain = entry.get('isSidechain', False)
    parent_uuid = entry.get('parentUuid')

    # Extract content based on type
    content: Any = None
    tool_calls: List[dict] = []
    tool_results: List[dict] = []

    if entry_type == 'summary':
        content = entry.get('summary', '')
    elif entry_type == 'system':
        content = entry.get('content', '')
    else:
        message = entry.get('message', {})
        raw_content = message.get('content', '')

        if isinstance(raw_content, str):
            content = raw_content
        elif isinstance(raw_content, list):
            # Process structured content
            text_parts = []
            for item in raw_content:
                if isinstance(item, str):
                    text_parts.append(item)
                elif isinstance(item, dict):
                    item_type = item.get('type', '')
                    if item_type == 'text':
                        text_parts.append(item.get('text', ''))
                    elif item_type == 'thinking':
                        # Include thinking as a special marker
                        thinking_text = item.get('thinking', '')
                        text_parts.append(f'<thinking>{thinking_text}</thinking>')
                    elif item_type == 'tool_use':
                        tool_calls.append({
                            'id': item.get('id'),
                            'name': item.get('name'),
                            'input': item.get('input', {}),
                        })
                    elif item_type == 'tool_result':
                        tool_results.append({
                            'tool_use_id': item.get('tool_use_id'),
                            'content': item.get('content'),
                            'is_error': item.get('is_error', False),
                        })

            content = {
                'text': '\n'.join(text_parts) if text_parts else '',
                'raw': raw_content,
            }
        else:
            content = str(raw_content)

    return ConversationMessage(
        type=entry_type,
        uuid=uuid,
        timestamp=timestamp,
        content=content,
        is_sidechain=is_sidechain,
        parent_uuid=parent_uuid,
        tool_calls=tool_calls,
        tool_results=tool_results,
        raw_entry=entry,
    )


def load_session_history(session_id: str) -> List[ConversationMessage]:
    """Load full conversation history from a session JSONL file."""
    session_path = Path(decode_session_id(session_id))

    if not session_path.exists():
        raise FileNotFoundError(f"Session not found: {session_id}")

    messages = []

    with open(session_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue

            message = parse_jsonl_entry(entry)
            if message:
                messages.append(message)

    return messages


def format_context_for_injection(
    messages: List[ConversationMessage],
    max_chars: int = 100000
) -> str:
    """
    Format conversation history for injection into Claude's context.

    Args:
        messages: List of conversation messages
        max_chars: Maximum characters to include

    Returns:
        Formatted string suitable for system prompt injection
    """
    lines = []
    current_chars = 0

    for msg in messages:
        if msg.is_sidechain:
            continue

        role_label = "Human" if msg.type == "user" else "Claude"

        # Extract text content
        if isinstance(msg.content, dict):
            text = msg.content.get('text', '')
        else:
            text = str(msg.content)

        # Cap individual messages
        content = text[:3000] if len(text) > 3000 else text
        line = f"**{role_label}**: {content}\n\n"

        if current_chars + len(line) > max_chars:
            lines.append("... [earlier context truncated] ...")
            break

        lines.append(line)
        current_chars += len(line)

    return "".join(lines)


def get_session_summary(session_id: str, max_messages: int = 10) -> str:
    """
    Get a brief summary of a session for display.

    Args:
        session_id: Session ID
        max_messages: Maximum number of messages to include

    Returns:
        Formatted summary string
    """
    try:
        messages = load_session_history(session_id)
    except FileNotFoundError:
        return "Session not found"

    if not messages:
        return "Empty session"

    lines = []
    for msg in messages[:max_messages]:
        if msg.is_sidechain:
            continue

        role = "Human" if msg.type == "user" else "Claude"

        if isinstance(msg.content, dict):
            text = msg.content.get('text', '')
        else:
            text = str(msg.content)

        content = text[:200]
        if len(text) > 200:
            content += "..."
        lines.append(f"[{role}]: {content}")

    if len(messages) > max_messages:
        lines.append(f"... and {len(messages) - max_messages} more messages")

    return "\n".join(lines)
