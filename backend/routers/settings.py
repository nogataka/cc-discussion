"""設定API"""

from fastapi import APIRouter
from pydantic import BaseModel

from backend.services.settings import (
    ToolPermissionMode,
    load_settings,
    save_settings,
)

router = APIRouter(prefix="/api/settings", tags=["settings"])


class SettingsResponse(BaseModel):
    """設定レスポンス"""

    tool_permission_mode: str


class SettingsUpdateRequest(BaseModel):
    """設定更新リクエスト"""

    tool_permission_mode: str


@router.get("", response_model=SettingsResponse)
async def get_settings():
    """現在の設定を取得"""
    settings = load_settings()
    return SettingsResponse(**settings)


@router.put("", response_model=SettingsResponse)
async def update_settings(request: SettingsUpdateRequest):
    """設定を更新"""
    # バリデーション
    mode = ToolPermissionMode(request.tool_permission_mode)
    settings = {"tool_permission_mode": mode.value}
    save_settings(settings)
    return SettingsResponse(**settings)


@router.get("/tool-permissions")
async def get_tool_permissions():
    """ツール許可状況の詳細を取得"""
    settings = load_settings()
    mode = settings["tool_permission_mode"]

    return {
        "current_mode": mode,
        "claude_code": {
            "read_only": ["Read", "Grep", "Glob", "WebFetch", "WebSearch"],
            "system_default": [
                "Read",
                "Grep",
                "Glob",
                "WebFetch",
                "WebSearch",
                "Edit",
                "Write",
                "Bash",
                "Task",
                "TodoWrite",
                "NotebookEdit",
            ],
        },
        "codex": {
            "read_only": ["read_file", "list_dir", "web_search", "url_fetch"],
            "system_default": [
                "read_file",
                "list_dir",
                "web_search",
                "url_fetch",
                "shell",
                "apply_patch",
            ],
        },
    }
