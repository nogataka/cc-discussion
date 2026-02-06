"""
Meeting Prompts
===============

会議タイプ別のプロンプトとファシリテーター用プロンプトを定義。

Note: This module uses string keys for meeting types to avoid import issues
when used in subprocess scripts.
"""

from typing import Optional, Union

# Try to import MeetingType for backwards compatibility with existing code
# that passes MeetingType enum values
try:
    from ..models.database import MeetingType
    _HAS_MEETING_TYPE_ENUM = True
except ImportError:
    _HAS_MEETING_TYPE_ENUM = False
    MeetingType = None  # type: ignore


def _normalize_meeting_type(meeting_type: Union[str, "MeetingType", None]) -> Optional[str]:
    """Convert meeting type to string key."""
    if meeting_type is None:
        return None
    if isinstance(meeting_type, str):
        return meeting_type
    # It's an Enum
    return meeting_type.value


# 会議タイプ別プロンプト (using string keys)
MEETING_TYPE_PROMPTS = {
    "progress_check": """## 会議タイプ: 進捗・状況確認

この会議では以下を議論します:
- 開発進捗の共有
- スケジュール遅延・ブロッカーの把握
- 依存関係（他チーム・外部）の確認

議論のポイント:
1. 現在の進捗を具体的に共有する
2. 予定との差異を明確にする
3. ブロッカーや課題を早期に特定する
4. 必要なサポートや調整事項を明確にする
""",

    "spec_alignment": """## 会議タイプ: 要件・仕様の認識合わせ

この会議では以下を議論します:
- 要件定義・仕様内容の確認
- 解釈差分・曖昧点の解消
- 仕様変更の影響範囲確認

議論のポイント:
1. 仕様の解釈に相違がないか確認する
2. 曖昧な点を具体化・明確化する
3. エッジケースや境界条件を洗い出す
4. 変更による影響範囲を特定する
""",

    "technical_review": """## 会議タイプ: 技術検討・設計判断

この会議では以下を議論します:
- アーキテクチャ・技術選定の検討
- 実装方針・設計方針の決定
- トレードオフ（性能・コスト・保守性）の整理

議論のポイント:
1. 複数の選択肢を比較検討する
2. 各選択肢のメリット・デメリットを明確にする
3. 将来の拡張性・保守性を考慮する
4. 具体的な判断基準と結論を出す
""",

    "issue_resolution": """## 会議タイプ: 課題・不具合対応

この会議では以下を議論します:
- 技術的課題・リスクの洗い出し
- 不具合の原因分析
- 対応方針・優先度の決定

議論のポイント:
1. 問題の再現手順と影響範囲を確認する
2. 根本原因を特定する
3. 複数の対応策を検討する
4. 対応の優先度とスケジュールを決める
""",

    "review": """## 会議タイプ: レビュー

この会議では以下を議論します:
- 設計レビュー
- 実装レビュー（コード・構成）
- テスト結果・品質確認

議論のポイント:
1. 設計・コードの品質を客観的に評価する
2. 改善点を具体的に指摘する
3. ベストプラクティスとの比較を行う
4. 建設的なフィードバックを心がける
""",

    "planning": """## 会議タイプ: 計画・タスク整理

この会議では以下を議論します:
- 開発タスクの分解・整理
- 担当者・期限の明確化
- 次スプリント／次フェーズの計画

議論のポイント:
1. タスクを適切な粒度に分解する
2. 依存関係と優先順位を明確にする
3. リスクと対策を事前に検討する
4. 現実的なスケジュールを設定する
""",

    "release_ops": """## 会議タイプ: リリース・運用判断

この会議では以下を議論します:
- リリース可否判断
- デプロイ手順・切り戻し確認
- 運用・監視観点の確認

議論のポイント:
1. リリース品質の最終確認を行う
2. デプロイ手順とロールバック手順を確認する
3. 監視項目とアラート閾値を確認する
4. 緊急時の連絡体制を確認する
""",

    "retrospective": """## 会議タイプ: 改善・振り返り

この会議では以下を議論します:
- 開発プロセスの振り返り
- ボトルネック・無駄の特定
- 改善アクションの決定

議論のポイント:
1. 良かった点（Keep）を共有する
2. 問題点（Problem）を特定する
3. 試してみたいこと（Try）を提案する
4. 具体的な改善アクションを決める
""",

    "other": """## 会議タイプ: その他

{custom_description}
""",
}


# 言語指示
LANGUAGE_INSTRUCTIONS = {
    "ja": "あなたは日本語で議論に参加します。全ての発言は日本語で行ってください。",
    "en": "You participate in the discussion in English. All your responses should be in English.",
}


# 会議タイプの日本語名
MEETING_TYPE_NAMES = {
    "progress_check": "進捗・状況確認",
    "spec_alignment": "要件・仕様の認識合わせ",
    "technical_review": "技術検討・設計判断",
    "issue_resolution": "課題・不具合対応",
    "review": "レビュー",
    "planning": "計画・タスク整理",
    "release_ops": "リリース・運用判断",
    "retrospective": "改善・振り返り",
    "other": "その他",
}


# ファシリテーターシステムプロンプト
FACILITATOR_SYSTEM_PROMPT = """## ファシリテーター役

あなたはこの会議のファシリテーターです。

### 役割
1. **会議開始時**: 会議の目的とゴールを説明し、議論のポイントを伝える
2. **議論中**: 議論が脱線しないよう軌道修正し、全員が発言できるよう促す
3. **会議終了時**: 議論の要点と決定事項をまとめ、次のアクションを明確にする

### 発言の指名方法
特定の参加者に発言を求める場合は、@メンションを使用してください。
例: 「@Claude_A さん、この点についてどう思いますか？」

複数の参加者に発言を求める場合:
例: 「@Claude_A と @Claude_B に意見を聞きたいです」

### 行動指針
- 中立的な立場を保つ
- 議論を深める質問を投げかける
- 合意形成をサポートする
- 目的とゴールから外れないよう注意する
- 必要に応じて@メンションで特定の参加者を指名する

### コンテキスト
あなたはこのプロジェクトのコードベースを理解しています。
技術的な質問があれば、コードを参照して具体的な情報を提供できます。
"""


# ファシリテーターオープニングテンプレート
FACILITATOR_OPENING_TEMPLATE = """皆さん、会議を始めましょう。

本日の会議タイプは「{meeting_type_name}」です。

### 本日の目的
{meeting_type_description}

### 議題
{topic}

### 参加者
{participants_list}

それでは議論を始めましょう。@{first_speaker} さんからお願いします。
"""


# ファシリテーター介入プロンプト
FACILITATOR_INTERJECTION_PROMPT = """【重要】これは会議の途中の簡単な確認です。まとめや結論を出す時間ではありません。

以下のいずれか1つだけを、1〜2文で簡潔に行ってください:
- 参加者から質問されていれば答える
- 議論が脱線していれば「〇〇に戻りましょう」と軌道修正
- 特定の参加者に質問や意見を求める（@参加者名 で指名）
- 次に議論すべき点を1つ提示
- 特に問題なければ「議論を続けてください」と促す

【発言の指名】
特定の参加者に発言を求める場合は @参加者名 を使用してください。
例: 「@Claude_A さん、この点について補足をお願いします」

【禁止事項】
- 長いまとめや要点整理は禁止（クロージングで行います）
- 箇条書きのリスト作成は禁止
- 決定事項やアクションの整理は禁止

短く、1〜2文で発言してください。"""


# 参加者の発言指名指示（チェーン駆動型）
PARTICIPANT_NOMINATION_INSTRUCTION = """
### 発言の終わり方
発言の最後に、次に発言すべき参加者を @参加者名 で指名してください。

例:
- 「...以上です。@Claude_B さん、技術的な観点からいかがですか？」
- 「...と思います。@Claude_C 、この点について補足をお願いします。」
- 「全員の意見を聞きたいので、@ALL お願いします。」
- 「この点は人間の判断が必要です。@モデレーター 、ご意見をいただけますか？」

【重要】
- 必ず発言の最後に次の発言者を指名してください
- 指名がない場合、ファシリテーターが代わりに指名します
- 議論を深めるために、関連する知見を持つ人を指名してください
- @ALL を使うと、参加者全員が順番に発言します
- @モデレーター を使うと、人間のモデレーターに質問・確認ができます（議論は一時停止します）
"""


# ファシリテーター指名介入プロンプト（指名がない場合）
FACILITATOR_DESIGNATION_PROMPT = """次の発言者を指名してください。

【指名のポイント】
- 発言回数が少ない参加者を優先
- 議論の文脈に関連する知見を持つ人を選ぶ
- 具体的な質問や論点を添えて指名

【必須】必ず @参加者名 で1人以上を指名してください。
全員に聞きたい場合は @ALL を使用してください。
議論が十分と判断したら @END で終了できます。

例: 「@Claude_A さん、先ほどの〇〇について詳しく教えてください」
例: 「議論は十分に深まりました。@END」

【参加者の発言回数】
{participation_stats}

短く、1〜2文で発言してください。"""


# ファシリテータークロージングプロンプト
FACILITATOR_CLOSING_PROMPT = """【会議のクロージング】これは会議の終了時のまとめです。詳細に整理してください。

以下の形式で会議をまとめてください:

## 議論の要点まとめ
- 主要な議論内容を箇条書きで整理

## 決定事項
- 今回の会議で決まったこと（なければ「特になし」）

## 未解決の課題
- 議論が必要な残課題（あれば）

## 次のアクション
- 誰が何をいつまでにやるか（具体的に）

参加者の発言を踏まえて、漏れなく整理してください。"""


# ファシリテータークロージングテンプレート
FACILITATOR_CLOSING_TEMPLATE = """お疲れ様でした。会議を締めくくります。

### 本日の議論のまとめ
{summary}

### 決定事項
{decisions}

### 次のアクション
{next_actions}

以上で会議を終了します。ありがとうございました。
"""


def get_meeting_type_prompt(
    meeting_type: Union[str, "MeetingType", None],
    custom_description: str = ""
) -> str:
    """会議タイプに応じたプロンプトを取得"""
    key = _normalize_meeting_type(meeting_type)
    if key is None:
        return ""
    prompt = MEETING_TYPE_PROMPTS.get(key, "")
    if key == "other" and custom_description:
        return prompt.format(custom_description=custom_description)
    return prompt


def get_language_instruction(language: str) -> str:
    """言語に応じた指示を取得"""
    return LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["ja"])


def get_meeting_type_name(meeting_type: Union[str, "MeetingType", None]) -> str:
    """会議タイプの日本語名を取得"""
    key = _normalize_meeting_type(meeting_type)
    if key is None:
        return "その他"
    return MEETING_TYPE_NAMES.get(key, "その他")


def get_facilitator_opening(
    meeting_type: Union[str, "MeetingType", None],
    topic: str,
    participants: list[str],
    first_speaker: str,
    custom_description: str = ""
) -> str:
    """ファシリテーターのオープニングメッセージを生成"""
    meeting_type_name = get_meeting_type_name(meeting_type)
    meeting_type_description = get_meeting_type_prompt(meeting_type, custom_description)

    # 参加者リストを整形
    participants_list = "\n".join([f"- {p}" for p in participants])

    return FACILITATOR_OPENING_TEMPLATE.format(
        meeting_type_name=meeting_type_name,
        meeting_type_description=meeting_type_description.strip(),
        topic=topic or "(議題なし)",
        participants_list=participants_list,
        first_speaker=first_speaker,
    )


def get_facilitator_closing(
    summary: str,
    decisions: str,
    next_actions: str
) -> str:
    """ファシリテーターのクロージングメッセージを生成"""
    return FACILITATOR_CLOSING_TEMPLATE.format(
        summary=summary,
        decisions=decisions,
        next_actions=next_actions,
    )
