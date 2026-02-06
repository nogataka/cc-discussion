"""
Mention Parser
==============

@メンションを解析して、指名された参加者を特定する。
"""

import re
from typing import Optional, List, Any
from dataclasses import dataclass


@dataclass
class MentionResult:
    """メンション解析結果"""
    mentioned_names: List[str]  # メンションされた名前のリスト
    has_mention: bool           # メンションが含まれているか
    clean_content: str          # メンションを除いた本文
    is_all: bool = False        # @ALL が含まれているか
    is_end: bool = False        # @END が含まれているか（議論終了）
    is_moderator: bool = False  # @モデレーター が含まれているか


def parse_mentions(content: str) -> MentionResult:
    """
    メッセージからメンションを解析する。

    パターン:
    - @参加者名
    - @[参加者名]（スペースを含む名前用）
    - @Claude_A, @Claude-A など
    - @ALL, @all, @All（全員指名）

    Args:
        content: メッセージ本文

    Returns:
        MentionResult: 解析結果
    """
    # @ALL パターンをチェック
    is_all = bool(re.search(r'@ALL\b', content, re.IGNORECASE))

    # @END パターンをチェック（議論終了）
    is_end = bool(re.search(r'@END\b', content, re.IGNORECASE))

    # @モデレーター パターンをチェック（モデレーターへの質問/確認）
    # @モデレーター, @moderator, @Moderator など
    is_moderator = bool(re.search(r'@(?:モデレーター|moderator)\b', content, re.IGNORECASE))

    # パターン1: @[名前] (角括弧で囲まれた名前)
    bracket_pattern = r'@\[([^\]]+)\]'
    # パターン2: @名前 (英数字・日本語・アンダースコア・ハイフン)
    # "エージェント B" のようなスペース+1文字のサフィックスもサポート
    # ALL, END, モデレーター, moderator は別扱いなので除外
    simple_pattern = r'@((?!ALL\b|END\b|モデレーター\b|moderator\b)[\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF][\w\u3040-\u309F\u30A0-\u30FF\u4E00-\u9FFF\-_]*(?: [A-Za-z0-9])?)'

    mentioned_names = []

    # 角括弧パターンを先に処理
    bracket_matches = re.findall(bracket_pattern, content)
    mentioned_names.extend(bracket_matches)

    # 角括弧を除去した後にシンプルパターンを処理
    content_without_brackets = re.sub(bracket_pattern, '', content)
    simple_matches = re.findall(simple_pattern, content_without_brackets, re.IGNORECASE)
    mentioned_names.extend(simple_matches)

    # メンションを除去したクリーンなコンテンツ
    clean_content = re.sub(bracket_pattern, '', content)
    clean_content = re.sub(simple_pattern, '', clean_content)
    clean_content = re.sub(r'@ALL\b', '', clean_content, flags=re.IGNORECASE)
    clean_content = re.sub(r'@END\b', '', clean_content, flags=re.IGNORECASE)
    clean_content = re.sub(r'@(?:モデレーター|moderator)\b', '', clean_content, flags=re.IGNORECASE)
    clean_content = clean_content.strip()

    return MentionResult(
        mentioned_names=mentioned_names,
        has_mention=len(mentioned_names) > 0 or is_all or is_end or is_moderator,
        clean_content=clean_content,
        is_all=is_all,
        is_end=is_end,
        is_moderator=is_moderator,
    )


def find_mentioned_participant(
    content: str,
    participants: List[Any],
    exclude_facilitator: bool = True,
) -> Optional[int]:
    """
    メンションされた参加者のIDを返す。
    複数メンションの場合は最初のものを返す。

    Args:
        content: メッセージ本文
        participants: 参加者リスト（name, id属性を持つオブジェクト）
        exclude_facilitator: ファシリテーターを除外するか

    Returns:
        参加者ID、見つからない場合はNone
    """
    result = parse_mentions(content)

    if not result.has_mention:
        return None

    # 参加者名とIDのマッピング（大文字小文字を区別しない）
    name_to_id = {}
    for p in participants:
        if exclude_facilitator and p.name == "ファシリテーター":
            continue
        # 完全一致と部分一致の両方を登録
        name_to_id[p.name.lower()] = p.id
        # スペースをアンダースコアに変換したバージョンも登録
        name_to_id[p.name.lower().replace(' ', '_')] = p.id
        name_to_id[p.name.lower().replace(' ', '-')] = p.id

    # メンションされた名前から参加者を探す
    for mentioned_name in result.mentioned_names:
        normalized = mentioned_name.lower()
        if normalized in name_to_id:
            return name_to_id[normalized]

        # 部分一致も試す - 最も一致度が高いものを選ぶ
        best_match = None
        best_score = 0
        for name, pid in name_to_id.items():
            if normalized in name:
                # メンション文字列が名前に含まれている場合
                # スコア = メンション文字数 / 名前の文字数 (高いほど良い)
                score = len(normalized) / len(name)
                if score > best_score:
                    best_score = score
                    best_match = pid
            elif name in normalized:
                # 名前がメンション文字列に含まれている場合
                score = len(name) / len(normalized)
                if score > best_score:
                    best_score = score
                    best_match = pid

        if best_match is not None:
            return best_match

    return None


def find_all_mentioned_participants(
    content: str,
    participants: List[Any],
    exclude_facilitator: bool = True,
) -> List[int]:
    """
    メンションされた全ての参加者のIDリストを返す。

    Args:
        content: メッセージ本文
        participants: 参加者リスト（name, id属性を持つオブジェクト）
        exclude_facilitator: ファシリテーターを除外するか

    Returns:
        参加者IDのリスト
    """
    result = parse_mentions(content)

    if not result.has_mention:
        return []

    # 参加者名とIDのマッピング
    name_to_id = {}
    for p in participants:
        if exclude_facilitator and p.name == "ファシリテーター":
            continue
        name_to_id[p.name.lower()] = p.id
        name_to_id[p.name.lower().replace(' ', '_')] = p.id
        name_to_id[p.name.lower().replace(' ', '-')] = p.id

    mentioned_ids = []
    seen = set()

    for mentioned_name in result.mentioned_names:
        normalized = mentioned_name.lower()

        # 完全一致
        if normalized in name_to_id:
            pid = name_to_id[normalized]
            if pid not in seen:
                mentioned_ids.append(pid)
                seen.add(pid)
            continue

        # 部分一致 - 最も一致度が高いものを選ぶ
        best_match = None
        best_score = 0
        for name, pid in name_to_id.items():
            if pid in seen:
                continue
            if normalized in name:
                # メンション文字列が名前に含まれている場合
                score = len(normalized) / len(name)
                if score > best_score:
                    best_score = score
                    best_match = pid
            elif name in normalized:
                # 名前がメンション文字列に含まれている場合
                score = len(name) / len(normalized)
                if score > best_score:
                    best_score = score
                    best_match = pid

        if best_match is not None:
            mentioned_ids.append(best_match)
            seen.add(best_match)

    return mentioned_ids
