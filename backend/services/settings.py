"""アプリケーション設定の管理"""

import json
from enum import StrEnum
from pathlib import Path
from typing import TypedDict


class ToolPermissionMode(StrEnum):
    """ツール許可モード"""

    READ_ONLY = "read_only"
    SYSTEM_DEFAULT = "system_default"


class AppSettings(TypedDict):
    """アプリケーション設定の型定義"""

    tool_permission_mode: str


SETTINGS_DIR = Path.home() / ".cc-discussion"
SETTINGS_FILE = SETTINGS_DIR / "settings.json"

DEFAULT_SETTINGS: AppSettings = {
    "tool_permission_mode": ToolPermissionMode.READ_ONLY,
}


def load_settings() -> AppSettings:
    """設定を読み込む"""
    if SETTINGS_FILE.exists():
        with open(SETTINGS_FILE) as f:
            return {**DEFAULT_SETTINGS, **json.load(f)}
    return DEFAULT_SETTINGS.copy()


def save_settings(settings: AppSettings) -> None:
    """設定を保存する"""
    SETTINGS_DIR.mkdir(parents=True, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=2)


def get_tool_permission_mode() -> ToolPermissionMode:
    """現在のツール許可モードを取得"""
    settings = load_settings()
    return ToolPermissionMode(settings["tool_permission_mode"])
