# Discussion Room

![Discussion Room Screenshot](docs/assets/screenshot.png)

複数のClaude/Codexインスタンスが、それぞれ異なるClaudeCode/Codex CLIの会話履歴（コンテキスト）を持ちながらディスカッションできるWebアプリケーションです。

## 概要

Slackのような会議室を作成し、2〜3人のClaude/Codexを招待してディスカッションさせることができます。各Claude/Codexには過去のClaudeCode/Codex会話履歴を注入できるため、人間がコンテキストを橋渡しする必要なく、問題解決や状況確認を行えます。

### 主な特徴

| 機能                             | 説明                                                                           |
| -------------------------------- | ------------------------------------------------------------------------------ |
| **ClaudeCode/Codex履歴ブラウザ** | `~/.claude/projects/`および`~/.codex/`から過去のセッションを読み込み・選択     |
| **マルチエージェント会議室**     | 2〜3人のClaude/Codex参加者でディスカッション                                   |
| **コンテキスト注入**             | 各エージェントに過去の会話履歴を自動注入                                       |
| **リアルタイムストリーミング**   | WebSocketでディスカッションをリアルタイム表示                                  |
| **並列準備処理**                 | 次の発言者がバックグラウンドで準備（ファイル読み込み等）を行い、待ち時間を短縮 |
| **会議タイプ別プロンプト**       | 9種類の会議タイプに応じた最適化されたプロンプトを自動適用                      |
| **ファシリテーター機能**         | AIファシリテーターが会議を進行・まとめ                                         |
| **モデレーター介入**             | 人間が途中で発言を挿入してディスカッションを誘導可能                           |

## 必要要件

- Python 3.11以上
- Node.js 20.19以上 または 22.12以上
- Claude CLI（インストール済み＆ログイン済み）
- Codex CLI（オプション：Codexエージェントを使用する場合）

## インストール・起動

```bash
# リポジトリに移動
cd /path/to/cc-discussion

# 起動（初回は自動的にセットアップされます）
./start.sh
```

### 起動オプション

```bash
# 通常起動（プロダクションモード）
./start.sh

# 開発モード（Viteホットリロード付き）
./start.sh --dev

# カスタムポート指定
./start.sh --port 9000

# リモートアクセス許可（セキュリティ注意）
./start.sh --host 0.0.0.0
```

起動スクリプトは以下を自動的に行います：
1. Python仮想環境の作成
2. Python依存関係のインストール
3. npm依存関係のインストール
4. Reactフロントエンドのビルド
5. サーバー起動（デフォルト: http://127.0.0.1:8888）
6. ブラウザを自動で開く

---

## 使い方

### 1. 会議室を作成

1. 画面左上の「New Room」ボタンをクリック
2. 会議設定を入力：
   - **会議室名**: 識別しやすい名前
   - **トピック**: ディスカッションのテーマ（詳細に書くほど良い結果に）
   - **会議タイプ**: 9種類から選択（後述）
   - **最大ターン数**: 会議の長さを制御（デフォルト: 20）
   - **言語**: 日本語 or 英語
3. 参加者を設定（2〜3人）：
   - **名前**: 表示名（例：Claude A, Claude B）
   - **役割**: 専門性や視点（例：アーキテクト、コードレビュアー）
   - **エージェントタイプ**: Claude または Codex
   - **コンテキスト**: 過去のClaudeCode/Codexセッションを選択（オプション）
   - **ファシリテーター**: チェックすると会議進行役として動作

### 2. 会議タイプ

会議の目的に応じて最適化されたプロンプトが自動適用されます：

| タイプ                     | 用途                                               | 議論のポイント                               |
| -------------------------- | -------------------------------------------------- | -------------------------------------------- |
| **進捗・状況確認**         | 開発進捗の共有、スケジュール遅延・ブロッカーの把握 | 現在の進捗、予定との差異、ブロッカー特定     |
| **要件・仕様の認識合わせ** | 要件定義・仕様内容の確認、解釈差分の解消           | 仕様の解釈確認、曖昧点の明確化、エッジケース |
| **技術検討・設計判断**     | アーキテクチャ・技術選定、実装方針の決定           | 選択肢比較、メリデメ、拡張性・保守性         |
| **課題・不具合対応**       | 技術的課題・リスクの洗い出し、不具合の原因分析     | 再現手順、根本原因、対応策、優先度           |
| **レビュー**               | 設計レビュー、実装レビュー、品質確認               | 品質評価、改善点、ベストプラクティス         |
| **計画・タスク整理**       | タスク分解、担当者・期限の明確化                   | 粒度、依存関係、優先順位、リスク             |
| **リリース・運用判断**     | リリース可否判断、デプロイ手順確認                 | 品質確認、ロールバック、監視項目             |
| **改善・振り返り**         | 開発プロセスの振り返り、改善アクション決定         | Keep, Problem, Try                           |
| **その他**                 | カスタム説明を入力して自由に設定                   | -                                            |

### 3. コンテキストの選択

各参加者に過去のClaudeCode/Codex会話履歴を注入できます：

1. 参加者フォームで「Select History」をクリック
2. **ClaudeCode履歴**: `~/.claude/projects/`から読み込み
3. **Codex履歴**: `~/.codex/`から読み込み
4. プロジェクト → セッションの順に選択

選択したセッションの会話内容が、そのエージェントのシステムプロンプトに注入されます。これにより、エージェントは過去のやり取りを「記憶」した状態で議論に参加できます。

### 4. ディスカッションの実行

1. 会議室を作成後、自動的に会議室ページに移動
2. **Start**ボタンでディスカッション開始
3. エージェントがラウンドロビン方式で順番に発言
   - ファシリテーターがいる場合：オープニング → 参加者の議論 → クロージング
   - いない場合：参加者のみで議論
4. **Pause**で一時停止、**Stop**で終了

### 5. 並列準備処理（Parallel Preparation）

Discussion Roomの特徴的な機能として、**並列準備処理**があります：

- 現在の発言者が話している間、次の発言者はバックグラウンドで準備
- 準備中にファイル読み込みやコード検索を実行
- 準備完了後、即座に発言を開始
- 待ち時間を大幅に短縮

### 6. モデレーター介入

ディスカッション中に人間がモデレーターとして発言を挿入できます：

1. 画面下部のテキストボックスにメッセージを入力
2. Enter（またはSendボタン）で送信
3. 次のエージェントの発言時にモデレーターメッセージが考慮されます

用途例：
- 議論の方向性を修正
- 追加の情報や制約を提供
- 特定のトピックに焦点を当てるよう指示

---

## 技術スタック

### バックエンド

| 技術                 | 用途                      |
| -------------------- | ------------------------- |
| **FastAPI**          | 非同期REST API・WebSocket |
| **SQLAlchemy 2.0**   | ORM（宣言的マッピング）   |
| **SQLite**           | データベース（設定不要）  |
| **Claude Agent SDK** | Claudeエージェント制御    |
| **Codex SDK**        | Codexエージェント制御     |
| **Pydantic**         | リクエスト/レスポンス検証 |

### フロントエンド

| 技術                | 用途                                 |
| ------------------- | ------------------------------------ |
| **React 19**        | UIフレームワーク                     |
| **TypeScript**      | 型安全性                             |
| **Vite**            | ビルドツール・開発サーバー           |
| **Tailwind CSS v4** | ユーティリティファーストCSS          |
| **Radix UI**        | アクセシブルUIコンポーネント         |
| **TanStack Query**  | サーバー状態管理・データフェッチング |
| **React Router**    | クライアントサイドルーティング       |
| **Lucide React**    | アイコン                             |

---

## アーキテクチャ

### システム構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                         │
├─────────────────────────────────────────────────────────────────┤
│  RoomPage.tsx          │  CreateRoomModal.tsx  │  Slack-UI      │
│  - メッセージ表示      │  - 会議室作成         │  - メッセージ  │
│  - WebSocket接続       │  - 参加者設定         │  - サイドバー  │
│  - コントロール        │  - 履歴選択           │  - ステータス  │
└────────────┬───────────┴───────────┬───────────┴────────────────┘
             │ HTTP/REST             │ WebSocket
             ▼                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
├─────────────────────────────────────────────────────────────────┤
│  main.py               │  rooms.py           │  history.py       │
│  - アプリ初期化        │  - ルームCRUD       │  - 履歴API       │
│  - 静的ファイル配信    │  - 制御API          │  - プロジェクト  │
│  - ライフサイクル      │  - モデレーター     │  - セッション    │
├─────────────────────────────────────────────────────────────────┤
│                    websocket.py                                  │
│  - WebSocket接続管理   - リアルタイム配信   - ルーム別ブロード │
└────────────────────────────┬────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│               Services (オーケストレーション)                     │
├─────────────────────────────────────────────────────────────────┤
│  parallel_orchestrator.py          │  discussion_orchestrator.py │
│  - 並列準備処理                    │  - 逐次処理（フォールバック）│
│  - バックグラウンド準備            │                             │
│  - イベントキュー                  │                             │
├─────────────────────────────────────────────────────────────────┤
│  participant_agent.py              │  codex_agent.py             │
│  - Claude Agent SDK               │  - Codex SDK                │
│  - サブプロセス実行               │  - サブプロセス実行         │
├─────────────────────────────────────────────────────────────────┤
│  history_reader.py                 │  codex_history_reader.py    │
│  - ClaudeCode履歴読み込み          │  - Codex履歴読み込み        │
│  - JSONL解析                       │  - JSONL解析                │
├─────────────────────────────────────────────────────────────────┤
│  meeting_prompts.py                                              │
│  - 会議タイプ別プロンプト          - ファシリテータープロンプト │
└─────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Database (SQLite)                             │
├─────────────────────────────────────────────────────────────────┤
│  DiscussionRoom        │  RoomParticipant     │  DiscussionMessage│
│  - name, topic         │  - name, role        │  - role, content  │
│  - status              │  - context_*         │  - turn_number    │
│  - meeting_type        │  - is_facilitator    │  - created_at     │
│  - max_turns           │  - agent_type        │                   │
└─────────────────────────────────────────────────────────────────┘
```

### ディスカッションフロー

```
1. ルーム作成
   └─> 参加者登録 → コンテキスト読み込み → DB保存

2. ディスカッション開始 (POST /api/rooms/{id}/start)
   └─> Orchestrator初期化 → 参加者エージェント生成

3. ターン実行 (並列準備処理)
   ┌─────────────────────────────────────────────────────┐
   │  [発言者A] Speaking ──────────────────────────────► │
   │  [発言者B] ──── Preparing (background) ─────────►   │
   │  [発言者C] ──────────── Preparing (background) ──►  │
   └─────────────────────────────────────────────────────┘
   
   各ターン:
   a. 現在の発言者がレスポンス生成（ストリーミング）
   b. 次の2名がバックグラウンドで準備
   c. WebSocket経由でリアルタイム配信
   d. DB保存 → 次の発言者へ

4. 完了/一時停止
   └─> ステータス更新 → クリーンアップ
```

### データベースモデル

```
DiscussionRoom (会議室)
├── id: Integer (PK)
├── name: String(200)
├── topic: Text (nullable)
├── status: Enum(waiting/active/paused/completed)
├── meeting_type: Enum(9種類)
├── custom_meeting_description: Text (nullable)
├── language: String(10) = "ja"
├── max_turns: Integer = 20
├── current_turn: Integer = 0
├── created_at: DateTime
└── updated_at: DateTime

RoomParticipant (参加者)
├── id: Integer (PK)
├── room_id: Integer (FK → DiscussionRoom)
├── name: String(50)
├── role: String(100) (nullable)
├── color: String(7) = "#6366f1"
├── context_project_dir: String(500) (nullable)
├── context_session_id: String(100) (nullable)
├── context_summary: Text (nullable)
├── is_speaking: Boolean = False
├── message_count: Integer = 0
├── is_facilitator: Boolean = False
└── agent_type: Enum(claude/codex) = claude

DiscussionMessage (メッセージ)
├── id: Integer (PK)
├── room_id: Integer (FK → DiscussionRoom)
├── participant_id: Integer (FK → RoomParticipant, nullable)
├── role: String(20) = system/participant/moderator
├── content: Text
├── extra_data: JSON (nullable)
├── turn_number: Integer
└── created_at: DateTime
```

---

## プロジェクト構造

```
cc-discussion/
├── backend/                          # バックエンド（Python/FastAPI）
│   ├── main.py                       # FastAPIエントリポイント
│   ├── websocket.py                  # WebSocketハンドラ
│   ├── models/
│   │   └── database.py               # SQLAlchemyモデル・Enum定義
│   ├── routers/
│   │   ├── history.py                # 履歴閲覧API
│   │   └── rooms.py                  # ルームCRUD API
│   └── services/
│       ├── parallel_orchestrator.py  # 並列準備オーケストレーター
│       ├── discussion_orchestrator.py# 逐次オーケストレーター
│       ├── participant_agent.py      # Claudeエージェント
│       ├── codex_agent.py            # Codexエージェント
│       ├── history_reader.py         # ClaudeCode履歴パーサー
│       ├── codex_history_reader.py   # Codex履歴パーサー
│       └── meeting_prompts.py        # 会議タイプ別プロンプト
│
├── frontend/                         # フロントエンド（React/TypeScript）
│   ├── src/
│   │   ├── App.tsx                   # メインアプリ・ルーティング
│   │   ├── main.tsx                  # エントリポイント
│   │   ├── pages/
│   │   │   └── RoomPage.tsx          # ディスカッション表示
│   │   ├── components/
│   │   │   ├── CreateRoomModal.tsx   # ルーム作成モーダル
│   │   │   ├── ParticipantAvatar.tsx # 参加者アバター
│   │   │   ├── ErrorBoundary.tsx     # エラーハンドリング
│   │   │   ├── slack-ui/             # Slack風UIコンポーネント
│   │   │   │   ├── ChannelSidebar.tsx
│   │   │   │   ├── MessageList.tsx
│   │   │   │   ├── MessageGroup.tsx
│   │   │   │   ├── MessageInput.tsx
│   │   │   │   ├── RoomHeader.tsx
│   │   │   │   └── StatusIndicator.tsx
│   │   │   └── ui/                   # 汎用UIコンポーネント（shadcn/ui）
│   │   ├── hooks/
│   │   │   └── useRoomWebSocket.ts   # WebSocket状態管理
│   │   └── lib/
│   │       └── api.ts                # APIクライアント
│   ├── index.html
│   ├── vite.config.ts
│   ├── tailwind.config.ts
│   └── package.json
│
├── start.sh                          # 起動スクリプト（Unix）
├── start_ui.py                       # Pythonランチャー
├── requirements.txt                  # Python依存関係
├── pyproject.toml                    # Python設定
├── .env.example                      # 環境変数テンプレート
├── .gitignore                        # Git除外設定
└── discussion.db                     # SQLiteデータベース（自動生成）
```

---

## API リファレンス

### 履歴閲覧API

| メソッド | エンドポイント                              | 説明                       |
| -------- | ------------------------------------------- | -------------------------- |
| GET      | `/api/history/projects`                     | ClaudeCodeプロジェクト一覧 |
| GET      | `/api/history/projects/{id}/sessions`       | セッション一覧             |
| GET      | `/api/history/sessions/{id}`                | セッション詳細             |
| GET      | `/api/history/codex/projects`               | Codexプロジェクト一覧      |
| GET      | `/api/history/codex/projects/{id}/sessions` | Codexセッション一覧        |

### ルーム管理API

| メソッド | エンドポイント             | 説明                                 |
| -------- | -------------------------- | ------------------------------------ |
| POST     | `/api/rooms`               | ルーム作成                           |
| GET      | `/api/rooms`               | ルーム一覧                           |
| GET      | `/api/rooms/{id}`          | ルーム詳細（参加者・メッセージ含む） |
| DELETE   | `/api/rooms/{id}`          | ルーム削除                           |
| POST     | `/api/rooms/{id}/start`    | ディスカッション開始                 |
| POST     | `/api/rooms/{id}/pause`    | 一時停止                             |
| POST     | `/api/rooms/{id}/moderate` | モデレーター発言                     |

### WebSocket

| エンドポイント      | 説明                                                 |
| ------------------- | ---------------------------------------------------- |
| `WS /ws/rooms/{id}` | リアルタイム更新（メッセージ・ステータス・準備状況） |

**WebSocketイベントタイプ:**
- `message`: 新規メッセージ
- `status_change`: ルームステータス変更
- `participant_speaking`: 発言者変更
- `preparation_activity`: 準備中のアクティビティ
- `preparation_complete`: 準備完了

---

## 開発

### バックエンドのみ起動

```bash
source venv/bin/activate
python -m uvicorn backend.main:app --reload --port 8888
```

### フロントエンドのみ起動

```bash
cd frontend
npm run dev
```

### ビルド

```bash
cd frontend
npm run build
```

### コード品質

```bash
# Python linting
source venv/bin/activate
ruff check backend/
mypy backend/

# TypeScript type check
cd frontend
npx tsc --noEmit
```

---

## トラブルシューティング

### Claude CLIが見つからない

```bash
# Claude CLIをインストール
# https://claude.ai/download からダウンロード

# ログイン
claude login
```

### ポートが使用中

```bash
# 別のポートを指定
./start.sh --port 9000
```

### 仮想環境の問題

```bash
# 仮想環境を削除して再作成
rm -rf venv
./start.sh
```

### データベースのリセット

```bash
# データベースファイルを削除（全データ消失）
rm discussion.db
./start.sh
```

### Node.jsバージョンの問題

Vite 7.x は Node.js 20.19+ または 22.12+ を要求します。

```bash
# nvm使用時
nvm install 22
nvm use 22
```

---

## ライセンス

MIT License
