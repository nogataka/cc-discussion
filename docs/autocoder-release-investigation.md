# Autocoder（AutoForge）リリースの仕組み 調査報告

調査日: 2026-02-06

## 目次

1. [概要](#概要)
2. [リリースアーキテクチャ](#リリースアーキテクチャ)
3. [主要ファイルと役割](#主要ファイルと役割)
4. [リリース手順](#リリース手順)
5. [配布パッケージの構成](#配布パッケージの構成)
6. [Pythonの組み込み方法](#pythonの組み込み方法)
7. [ユーザー側のインストールフロー](#ユーザー側のインストールフロー)
8. [まとめ](#まとめ)

---

## 概要

Autocoderは **npmパッケージ** として公開される仕組みになっています。

| 項目             | 内容           |
| ---------------- | -------------- |
| パッケージ名     | `autoforge-ai` |
| 現在のバージョン | `0.1.3`        |
| CLIコマンド      | `autoforge`    |
| Node.js要件      | `>=20`         |
| Python要件       | `>=3.11`       |
| ライセンス       | AGPL-3.0       |

---

## リリースアーキテクチャ

```
┌──────────────────────────────────────────────────────────────────┐
│                         npm Registry                              │
│                     (autoforge-ai パッケージ)                      │
└──────────────────────────────────────────────────────────────────┘
                                 ↑
                          npm publish
                                 │
┌──────────────────────────────────────────────────────────────────┐
│                    ローカル開発環境                                │
├──────────────────────────────────────────────────────────────────┤
│  1. package.json のバージョン更新                                 │
│  2. prepublishOnly スクリプトでUIビルド                           │
│  3. .npmignore で不要ファイル除外                                  │
│  4. files フィールドで配布ファイル指定                             │
└──────────────────────────────────────────────────────────────────┘
```

---

## 主要ファイルと役割

### 1. `package.json` - パッケージ設定

```json
{
  "name": "autoforge-ai",
  "version": "0.1.3",
  "bin": {
    "autoforge": "./bin/autoforge.js"
  },
  "type": "module",
  "engines": {
    "node": ">=20"
  },
  "files": [
    "bin/", "lib/", "api/", "server/", "mcp_server/",
    "ui/dist/", "ui/package.json",
    ".claude/commands/", ".claude/templates/",
    "examples/", "start.py", "agent.py", ...
    "requirements-prod.txt", "pyproject.toml", ".env.example"
  ],
  "scripts": {
    "prepublishOnly": "npm --prefix ui install && npm --prefix ui run build"
  }
}
```

**キーポイント:**
- `bin.autoforge` → CLIエントリポイント
- `files` → 配布に含めるファイル一覧（明示的なホワイトリスト）
- `prepublishOnly` → `npm publish` 前にUIをビルド

### 2. `.npmignore` - 配布除外ファイル

```
venv/
**/__pycache__/
.git/
.github/
node_modules/
test_*.py
ui/src/           # ソースは除外、ui/dist/のみ配布
ui/node_modules/
start.sh          # 開発用スクリプトは除外
start_ui.sh
start_ui.py
CLAUDE.md
LICENSE.md
README.md
```

### 3. `bin/autoforge.js` - CLIエントリポイント

```javascript
#!/usr/bin/env node
import { run } from '../lib/cli.js';
run(process.argv.slice(2));
```

### 4. `lib/cli.js` - メインCLIロジック

Node.js純正モジュールのみ使用（外部依存なし）：
- Python環境の検出・セットアップ
- 仮想環境の作成・管理（`~/.autoforge/venv/`）
- 依存関係のインストール（`requirements-prod.txt`）
- uvicornサーバーの起動
- 設定ファイル管理（`~/.autoforge/.env`）

### 5. `.github/workflows/ci.yml` - CI設定

```yaml
name: CI
on:
  pull_request:
    branches: [master, main]
  push:
    branches: [master, main]

jobs:
  python:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Lint with ruff
        run: ruff check .
      - name: Run security tests
        run: python test_security.py

  ui:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: ui
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: '20'
      - name: Install dependencies
        run: npm ci
      - name: Lint
        run: npm run lint
      - name: Type check & Build
        run: npm run build
```

**現状のCIは「テストのみ」で、自動リリースは含まれていません。**

---

## リリース手順

### 手動リリースフロー（推定）

```bash
# 1. バージョン更新
# package.json の version を更新（例: "0.1.3" → "0.1.4"）

# 2. テスト実行
npm --prefix ui run build
python test_security.py
cd ui && npm run lint && npm run build

# 3. npmにpublish
npm publish
# → prepublishOnly でUIが自動ビルドされる
```

---

## 配布パッケージの構成

npmパッケージに含まれるもの：

| カテゴリ | ファイル/ディレクトリ                     | 説明                         |
| -------- | ----------------------------------------- | ---------------------------- |
| CLI      | `bin/autoforge.js`                        | エントリポイント             |
| CLI      | `lib/cli.js`                              | メインCLIロジック            |
| Python   | `server/`, `api/`                         | FastAPIバックエンド          |
| Python   | `agent.py`, `client.py`, etc.             | コアモジュール               |
| Python   | `requirements-prod.txt`                   | 本番用依存関係               |
| UI       | `ui/dist/`                                | **ビルド済み**フロントエンド |
| 設定     | `.env.example`                            | 設定テンプレート             |
| Claude   | `.claude/commands/`, `.claude/templates/` | ClaudeCode連携               |

---

## Pythonの組み込み方法

### アーキテクチャ概要

```
┌─────────────────────────────────────────────────────────────────────┐
│                        npm install -g autoforge-ai                   │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                         autoforge コマンド実行                        │
│                         (bin/autoforge.js)                           │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                          lib/cli.js                                  │
├─────────────────────────────────────────────────────────────────────┤
│  1. findPython()     → システムのPythonを検出                        │
│  2. ensureVenv()     → ~/.autoforge/venv/ に仮想環境作成             │
│  3. pip install      → requirements-prod.txt をインストール          │
│  4. spawn(uvicorn)   → Pythonサーバーを子プロセスで起動              │
└─────────────────────────────────────────────────────────────────────┘
                                    ↓
┌─────────────────────────────────────────────────────────────────────┐
│                   ~/.autoforge/venv/bin/python                       │
│                        (uvicorn + FastAPI)                           │
└─────────────────────────────────────────────────────────────────────┘
```

**重要なポイント**: Pythonはnpmパッケージに**同梱されていません**。ユーザーのシステムにインストール済みのPythonを**検出して利用**します。

### 1. Python検出 (`findPython()`)

```javascript
// lib/cli.js より抜粋

function findPython() {
  // 環境変数でオーバーライド可能
  const override = process.env.AUTOFORGE_PYTHON;
  if (override) {
    const result = tryPythonCandidate(override);
    // ...
  }

  // プラットフォーム別の検索順序
  const candidates = IS_WIN
    ? ['python', ['py', '-3'], 'python3']    // Windows
    : ['python3', 'python'];                  // macOS/Linux

  for (const candidate of candidates) {
    const result = tryPythonCandidate(candidate);
    if (!result) continue;
    
    // バージョン 3.11+ を要求
    if (result.tooOld) continue;
    
    // venvモジュールの存在確認（Debian/Ubuntuで必要）
    execFileSync(exe, ['-c', 'import ensurepip'], ...);
    
    return result;
  }
}
```

**検出ロジック**:
1. `AUTOFORGE_PYTHON` 環境変数があればそれを使用
2. プラットフォームに応じた候補を順番に試行
3. バージョン 3.11 以上であることを確認
4. `venv` モジュールが使えることを確認

### 2. 仮想環境の作成 (`ensureVenv()`)

```javascript
// 仮想環境のパス
const CONFIG_HOME = join(homedir(), '.autoforge');  // ~/.autoforge/
const VENV_DIR = join(CONFIG_HOME, 'venv');         // ~/.autoforge/venv/
const DEPS_MARKER = join(VENV_DIR, '.deps-installed');

function ensureVenv(python, forceRecreate) {
  // マーカーファイルで状態管理
  const marker = readMarker();
  const reqHash = requirementsHash();  // requirements-prod.txt のSHA-256
  
  // 仮想環境作成が必要かチェック
  let needsCreate = forceRecreate || !existsSync(pyExe);
  
  // Pythonバージョンが変わった場合も再作成
  if (marker.python_version !== currentMinor) {
    needsCreate = true;
  }
  
  // 依存関係が最新かチェック
  if (marker.requirements_hash !== reqHash) {
    depsUpToDate = false;
  }
  
  // 仮想環境作成
  if (needsCreate) {
    execFileSync(python.exe, ['-m', 'venv', VENV_DIR]);
  }
  
  // 依存関係インストール
  execFileSync(pyExe, ['-m', 'pip', 'install', '-q', '-r', REQUIREMENTS_FILE]);
  
  // マーカーファイル保存
  writeFileSync(DEPS_MARKER, JSON.stringify({
    requirements_hash: reqHash,
    python_version: `${major}.${minor}`,
    python_path: pyExe,
    created_at: new Date().toISOString(),
  }));
}
```

**キャッシュ機構**:
- `.deps-installed` マーカーファイルで状態管理
- `requirements-prod.txt` のハッシュで依存関係の変更を検知
- Pythonバージョン変更時は仮想環境を再作成

### 3. サーバー起動 (`startServer()`)

```javascript
function startServer(opts) {
  const pyExe = venvPython();  // ~/.autoforge/venv/bin/python
  
  // 環境変数を設定
  const serverEnv = { 
    ...process.env, 
    ...dotenvVars,              // ~/.autoforge/.env の内容
    PYTHONPATH: PKG_DIR         // npmパッケージのルートをPYTHONPATHに追加
  };
  
  // uvicorn を子プロセスで起動
  const child = spawn(
    pyExe,
    [
      '-m', 'uvicorn',
      'server.main:app',        // FastAPIアプリ
      '--host', host,
      '--port', String(port),
    ],
    {
      cwd: PKG_DIR,             // npmパッケージのルートディレクトリ
      env: serverEnv,
      stdio: 'inherit',         // 標準出力を継承
    }
  );
  
  writePid(child.pid);          // PIDファイル保存
  
  // ブラウザを開く
  setTimeout(() => openBrowser(`http://${host}:${port}`), 2000);
}
```

### 4. ファイル配置

```
npmパッケージ (autoforge-ai)
├── bin/autoforge.js          # CLIエントリポイント
├── lib/cli.js                # Python検出・起動ロジック（Node.js）
├── server/                   # FastAPIバックエンド（Python）
│   └── main.py
├── api/                      # API実装（Python）
├── agent.py                  # エージェントコア（Python）
├── client.py                 # クライアント（Python）
├── requirements-prod.txt     # Python依存関係
├── ui/dist/                  # ビルド済みフロントエンド
└── .env.example

ユーザーのホームディレクトリ
└── ~/.autoforge/
    ├── venv/                 # 仮想環境（自動作成）
    │   ├── bin/python        # Pythonインタプリタ
    │   ├── lib/              # site-packages
    │   └── .deps-installed   # 依存関係マーカー
    ├── .env                  # ユーザー設定
    └── server.pid            # 実行中サーバーのPID
```

---

## ユーザー側のインストールフロー

```bash
# グローバルインストール
npm install -g autoforge-ai

# 起動（初回は自動セットアップ）
autoforge
```

### 初回起動時の処理

```
[1/3] Checking Python...
      Found Python 3.11.x at /usr/bin/python3

[2/3] Setting up environment...
      Creating virtual environment at ~/.autoforge/venv/
      Installing dependencies...
      Done

[3/3] Starting server...
      Created config file: ~/.autoforge/.env

  Server running at http://127.0.0.1:8888
  Press Ctrl+C to stop
```

### 2回目以降の起動（高速パス）

依存関係が変わっていなければ、セットアップステップをスキップ：

```
  AutoForge v0.1.3

  Server running at http://127.0.0.1:8888
  Press Ctrl+C to stop
```

---

## まとめ

### リリースの仕組み

| 項目               | 内容                                    |
| ------------------ | --------------------------------------- |
| **配布形態**       | npm パッケージ（`autoforge-ai`）        |
| **バージョン管理** | `package.json` の `version` フィールド  |
| **ビルド**         | `prepublishOnly` フックでUIを自動ビルド |
| **CI**             | lint・テストのみ（自動リリースなし）    |
| **除外設定**       | `.npmignore` + `files` フィールド       |

### Pythonの組み込み

| 項目               | 内容                                            |
| ------------------ | ----------------------------------------------- |
| **Python同梱**     | なし（システムのPythonを利用）                  |
| **最低バージョン** | Python 3.11+                                    |
| **仮想環境**       | `~/.autoforge/venv/` に自動作成                 |
| **依存関係**       | `requirements-prod.txt` から `pip install`      |
| **サーバー起動**   | Node.jsから `spawn()` でuvicornを子プロセス起動 |
| **状態管理**       | `.deps-installed` マーカーファイルでキャッシュ  |

### メリット・デメリット

**メリット**:
- npmパッケージサイズを小さく保てる（Pythonランタイムを含まない）
- ユーザーのPython環境を尊重
- 仮想環境で依存関係を隔離
- 2回目以降の起動が高速

**デメリット**:
- ユーザーがPython 3.11+をインストールしている必要がある
- 初回起動時に依存関係インストールで時間がかかる

### 改善提案

現在のリリースは手動なので、以下の自動化が考えられます：

1. **タグベースの自動リリース**: `v*` タグpush時に自動 `npm publish`
2. **Changelogの自動生成**: conventional commits + semantic-release
3. **バージョンバンプの自動化**: `npm version patch/minor/major` の活用
