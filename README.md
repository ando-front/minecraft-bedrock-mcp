# minecraft-bedrock-mcp

Minecraft Bedrock Edition を [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) 経由で操作するためのサーバー。Claude などの MCP クライアントから自然言語で建築・地形生成・コマンド実行を指示できる。

## 特徴

- **MCP サーバーと WebSocket サーバーを 1 プロセスに同居**: Minecraft Bedrock の `/connect` で接続するための WebSocket サーバーと、Claude が接続するための MCP サーバーを単一プロセスで起動
- **拡張性重視の builder レジストリ**: `@builder` デコレータを付けた関数を `builders/` 配下に置くだけで、新しい建築コマンドを追加可能。既存コードの変更は不要
- **3 階層の tool 公開**: 低レベルプリミティブ (`setblock` 等) / クエリ / 高レベル builder の 3 階層で MCP tool を提供。試行錯誤と定型化の両方をカバー
- **WebSocket 単独モードも維持**: MCP を使わず、従来のチャットコマンド経由でも動かせる

## アーキテクチャ

```
Claude (Desktop / Code)
  ↕ MCP (stdio)
MCP サーバー (Python)
  ↕ 内部呼び出し
WebSocket サーバー
  ↕ WebSocket (ws://localhost:8000)
Minecraft Bedrock Edition (/connect)
```

## 必要環境

- Python 3.11 以上
- Minecraft Bedrock Edition (Windows / Mobile / Switch 等)
- チート有効・シングルプレイまたは LAN 接続 (Realms 不可)

## セットアップ

[uv](https://docs.astral.sh/uv/) を推奨。

```bash
git clone https://github.com/<your-account>/minecraft-bedrock-mcp.git
cd minecraft-bedrock-mcp
uv sync
```

## 使い方

### モード 1: WebSocket 単独 (チャットコマンド)

```bash
uv run python server.py
```

Minecraft 内のチャットで:

```
/connect localhost:8000
tower 30 diamond_block
```

### モード 2: MCP サーバー (Claude から操作)

`claude_desktop_config.json` に追加:

```json
{
  "mcpServers": {
    "minecraft-bedrock": {
      "command": "uv",
      "args": [
        "--directory",
        "/absolute/path/to/minecraft-bedrock-mcp",
        "run",
        "python",
        "mcp_server.py"
      ]
    }
  }
}
```

Claude Desktop を再起動後、Minecraft 内で `/connect localhost:8000` を実行。以降は Claude に自然言語で指示できる。

## 新しい builder の追加

`src/mc_bedrock_mcp/builders/` に新しいファイルを追加するだけ:

```python
# src/mc_bedrock_mcp/builders/spiral_staircase.py
from ..registry import builder
from ..mc import MinecraftClient

@builder("spiral_staircase")
async def spiral_staircase(
    mc: MinecraftClient,
    height: int = 20,
    radius: int = 5,
    block: str = "stone",
) -> str:
    """指定した高さと半径で螺旋階段を建築する。"""
    # 実装
    return f"建築完了: 高さ {height}, 半径 {radius}"
```

これだけで以下が自動的に有効になる:

- チャットコマンド: `spiral_staircase 20 5 stone`
- MCP tool: `mc_build_spiral_staircase(height=20, radius=5, block="stone")`

## ディレクトリ構成

```
minecraft-bedrock-mcp/
├── src/mc_bedrock_mcp/
│   ├── mc.py                 # WebSocket クライアント抽象
│   ├── registry.py           # @builder デコレータ + MCP スキーマ生成
│   ├── schemas.py            # Pydantic モデル (座標、ブロック等)
│   └── builders/             # 建築モジュール (拡張ポイント)
├── server.py                 # WebSocket 単独起動
├── mcp_server.py             # MCP + WebSocket 同居起動
└── tests/
```

## ライセンス

MIT
