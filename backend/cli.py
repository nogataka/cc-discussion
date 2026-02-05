"""
cc-discussion CLI
=================

uvx cc-discussion または python -m backend で実行

Usage:
    cc-discussion                    # デフォルト設定で起動
    cc-discussion --port 9000        # ポート指定
    cc-discussion --no-browser       # ブラウザを開かない
    cc-discussion --reload           # 開発モード（ホットリロード）
"""
import webbrowser
from threading import Timer

import click
import uvicorn


@click.command()
@click.option('--host', default='127.0.0.1', help='バインドするホスト')
@click.option('--port', default=8888, type=int, help='バインドするポート')
@click.option('--no-browser', is_flag=True, help='ブラウザを自動で開かない')
@click.option('--reload', is_flag=True, help='ホットリロードを有効化（開発用）')
@click.version_option(version='1.0.0', prog_name='cc-discussion')
def main(host: str, port: int, no_browser: bool, reload: bool):
    """Claude Discussion Room - マルチエージェント議論プラットフォーム"""
    url = f"http://{host}:{port}"
    click.echo(f"Starting cc-discussion on {url}")

    # ブラウザを少し遅らせて開く（サーバー起動を待つ）
    if not no_browser:
        Timer(1.5, lambda: webbrowser.open(url)).start()

    uvicorn.run(
        "backend.main:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == '__main__':
    main()
