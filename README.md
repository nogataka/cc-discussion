# Discussion Room

複数のClaude/Codexインスタンスが、それぞれ異なるClaudeCode/Codexの会話履歴（コンテキスト）を持ちながらディスカッションできるWebアプリケーションです。

## 概要

Slackのような会議室を作成し、2〜3人のClaude/Codexを招待してディスカッションさせることができます。各Claude/Codexには過去のClaudeCode/Codex会話履歴を注入できるため、人間がコンテキストを橋渡しする必要なく、問題解決や状況確認を行えます。

### 主な特徴

- **ClaudeCode/Codex履歴ブラウザ**: `~/.claude/projects/`から過去のセッションを読み込み・選択
- **マルチClaude/Codex会議室**: 2〜3人のClaude/Codex参加者でディスカッション
- **コンテキスト注入**: 各Claude/Codexに過去の会話履歴を自動注入
- **リアルタイムストリーミング**: WebSocketでディスカッションをリアルタイム表示
- **モデレーター介入**: 人間が途中で発言を挿入してディスカッションを誘導可能

## 必要要件

- Python 3.11以上
- Node.js 20.19以上 または 22.12以上
- Claude CLI（インストール済み＆ログイン済み）

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
5. サーバー起動
6. ブラウザを自動で開く

## 使い方

### 1. 会議室を作成

1. ホーム画面で「Create New Room」をクリック
2. 会議室名とディスカッションのトピックを入力
3. 参加者（2〜3人のClaude）を設定
   - 名前（例：Claude A, Claude B）
   - 役割（例：アーキテクト、コードレビュアー）
   - コンテキスト（オプション：ClaudeCodeの過去セッションを選択）

### 2. コンテキストの選択

各参加者に過去のClaudeCode会話履歴を注入できます：

1. 参加者フォームで「Select Context」をクリック
2. プロジェクト一覧から選択
3. セッション一覧から関連するセッションを選択

選択したセッションの会話内容が、そのClaudeのシステムプロンプトに注入されます。

### 3. ディスカッションの開始

1. 会議室を作成後、自動的に会議室ページに移動
2. 「Start」ボタンでディスカッション開始
3. Claudeがラウンドロビン方式で順番に発言
4. 必要に応じて「Pause」で一時停止

### 4. モデレーター介入

ディスカッション中に人間がモデレーターとして発言を挿入できます：

1. 画面下部のテキストボックスにメッセージを入力
2. Enter（またはSendボタン）で送信
3. 次のClaudeの発言時にモデレーターメッセージが考慮されます

## 技術スタック

### バックエンド
- **FastAPI** - 非同期REST API
- **SQLAlchemy** - ORM
- **SQLite** - データベース
- **WebSocket** - リアルタイム通信
- **Claude Agent SDK** - マルチエージェント調整

### フロントエンド
- **React 19** - UIフレームワーク
- **TypeScript** - 型安全性
- **Vite** - ビルドツール
- **Tailwind CSS v4** - スタイリング
- **Radix UI** - UIコンポーネント
- **TanStack Query** - データフェッチング
- **React Router** - ルーティング

## プロジェクト構造

```
cc-discussion/
├── backend/
│   ├── main.py                     # FastAPIエントリポイント
│   ├── websocket.py                # WebSocketハンドラ
│   ├── models/
│   │   └── database.py             # SQLAlchemyモデル
│   ├── services/
│   │   ├── history_reader.py       # ClaudeCode履歴パーサー
│   │   └── discussion_orchestrator.py  # マルチエージェント調整
│   └── routers/
│       ├── history.py              # 履歴閲覧API
│       └── rooms.py                # ルームCRUD API
├── frontend/
│   └── src/
│       ├── App.tsx                 # メインアプリ
│       ├── pages/
│       │   ├── HomePage.tsx        # ルーム一覧・作成
│       │   └── RoomPage.tsx        # ディスカッション表示
│       ├── components/
│       │   └── CreateRoomModal.tsx # ルーム作成モーダル
│       ├── hooks/
│       │   └── useRoomWebSocket.ts # WebSocket状態管理
│       └── lib/
│           └── api.ts              # APIクライアント
├── start.sh                        # 起動スクリプト（Unix）
├── start_ui.py                     # Pythonランチャー
├── requirements.txt                # Python依存関係
└── discussion.db                   # SQLiteデータベース（自動生成）
```

## API エンドポイント

### 履歴閲覧
- `GET /api/history/projects` - ClaudeCodeプロジェクト一覧
- `GET /api/history/projects/{dir}/sessions` - セッション一覧
- `GET /api/history/projects/{dir}/sessions/{id}` - セッションのメッセージ

### ルーム管理
- `POST /api/rooms` - ルーム作成
- `GET /api/rooms` - ルーム一覧
- `GET /api/rooms/{id}` - ルーム詳細
- `DELETE /api/rooms/{id}` - ルーム削除
- `POST /api/rooms/{id}/start` - ディスカッション開始
- `POST /api/rooms/{id}/pause` - 一時停止
- `POST /api/rooms/{id}/moderate` - モデレーター発言

### WebSocket
- `WS /ws/rooms/{id}` - リアルタイム更新

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

## ライセンス

MIT License
