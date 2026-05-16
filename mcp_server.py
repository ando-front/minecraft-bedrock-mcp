"""MCP + WebSocket サーバーを 1 プロセスで同居起動するエントリポイント。

- WebSocket サーバー: Minecraft Bedrock が `/connect localhost:8000` で接続
- MCP サーバー: Claude Desktop などの MCP クライアントが stdio で接続

Claude が MCP tool を呼び出すと、内部で WebSocket 経由で Minecraft にコマンドが送られる。
"""

from __future__ import annotations

import asyncio
import logging

from fastmcp import FastMCP

from mc_bedrock_mcp.mc import MinecraftServer
from mc_bedrock_mcp.registry import (
    all_builders,
    invoke,
    load_builtin_builders,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# WebSocket サーバーのグローバルインスタンス (MCP tool から参照される)
mc_server = MinecraftServer(host="localhost", port=8000)

# MCP サーバー本体
mcp = FastMCP("minecraft-bedrock-mcp")


# --- Layer 2: クエリ tool ---

@mcp.tool()
async def mc_get_connection_status() -> dict:
    """Minecraft Bedrock との接続状態を返す。

    Returns:
        connected (bool): 接続中なら True
        hint (str): 未接続時の対処方法
    """
    connected = mc_server.current is not None
    return {
        "connected": connected,
        "hint": (
            "Minecraft 内で `/connect localhost:8000` を実行してください。"
            if not connected
            else "Connected."
        ),
    }


@mcp.tool()
async def mc_list_builders() -> list[dict]:
    """登録済み builder の一覧を返す。"""
    return [{"name": b.name, "description": b.doc} for b in all_builders()]


# --- Layer 1: プリミティブ tool ---

@mcp.tool()
async def mc_setblock(x: int, y: int, z: int, block: str) -> str:
    """指定座標に 1 ブロック配置する。

    Args:
        x, y, z: 配置座標
        block: ブロック ID (例: "stone", "diamond_block")
    """
    client = mc_server.current
    if client is None:
        return "Error: Minecraft is not connected. Run /connect localhost:8000 in-game."
    await client.setblock(x, y, z, block)
    return f"setblock ({x},{y},{z}) {block}"


@mcp.tool()
async def mc_fill(
    x1: int, y1: int, z1: int,
    x2: int, y2: int, z2: int,
    block: str,
) -> str:
    """直方体領域をブロックで埋める。

    大きな構造物では setblock のループより遥かに高速。
    """
    client = mc_server.current
    if client is None:
        return "Error: Minecraft is not connected. Run /connect localhost:8000 in-game."
    await client.fill(x1, y1, z1, x2, y2, z2, block)
    return f"fill ({x1},{y1},{z1})-({x2},{y2},{z2}) {block}"


@mcp.tool()
async def mc_run_command(command: str) -> str:
    """任意の Minecraft コマンドを実行する (エスケープハッチ)。

    Args:
        command: `/` を含まないコマンド文字列 (例: "tp @s 0 100 0")
    """
    client = mc_server.current
    if client is None:
        return "Error: Minecraft is not connected. Run /connect localhost:8000 in-game."
    result = await client.run_command(command)
    return f"OK: {result}"


@mcp.tool()
async def mc_say(message: str) -> str:
    """ゲーム内チャットにメッセージを表示する。"""
    client = mc_server.current
    if client is None:
        return "Error: Minecraft is not connected."
    await client.say(message)
    return f"say: {message}"


# --- Layer 3: 高レベル builder tool (動的登録) ---

def _register_builder_tools() -> None:
    """登録済み builder を MCP tool として動的に公開する。"""
    for entry in all_builders():
        _register_one_builder(entry.name)


def _register_one_builder(name: str) -> None:
    """1 つの builder を MCP tool として登録する。

    クロージャで name をキャプチャすることで、複数 builder の登録時に
    変数が上書きされないようにする。
    """

    async def tool_fn(**kwargs) -> str:
        client = mc_server.current
        if client is None:
            return "Error: Minecraft is not connected. Run /connect localhost:8000 in-game."
        try:
            result = await invoke(name, client, **kwargs)
            return str(result)
        except Exception as exc:
            logger.exception("Builder %s failed", name)
            return f"Error: {exc}"

    tool_fn.__name__ = f"mc_build_{name}"
    # 元の builder の docstring と signature を継承
    from mc_bedrock_mcp.registry import get
    entry = get(name)
    if entry:
        tool_fn.__doc__ = entry.doc
    mcp.tool(name=f"mc_build_{name}")(tool_fn)


# --- 起動処理 ---

async def _run_websocket() -> None:
    """WebSocket サーバーをバックグラウンドで起動。"""
    await mc_server.serve()


def main() -> None:
    load_builtin_builders()
    _register_builder_tools()
    logger.info("Loaded builders: %s", [b.name for b in all_builders()])

    # FastMCP の起動と並行して WebSocket サーバーをバックグラウンドで動かす。
    # FastMCP の lifespan を使って起動するのが理想だが、
    # シンプルに別タスクで起動するアプローチを採用。
    async def _runner() -> None:
        ws_task = asyncio.create_task(_run_websocket())
        try:
            await mcp.run_async(transport="stdio")
        finally:
            ws_task.cancel()

    asyncio.run(_runner())


if __name__ == "__main__":
    main()
