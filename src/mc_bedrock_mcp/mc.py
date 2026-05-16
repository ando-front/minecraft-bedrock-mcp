"""Minecraft Bedrock との WebSocket 通信を担う低レベルクライアント。

`/connect` で接続してきた Minecraft クライアントに対して
コマンドを送信する責務を持つ。MCP 層からも WebSocket チャットコマンド層からも
共通で利用される。
"""

from __future__ import annotations

import asyncio
import json
import logging
import uuid
from typing import Any

import websockets
from websockets.legacy.server import WebSocketServerProtocol

logger = logging.getLogger(__name__)


class MinecraftClient:
    """単一の Minecraft クライアントへのコマンド送信を担う。

    `/connect` でこのサーバーに接続してきた WebSocket セッションを保持し、
    `commandRequest` メッセージを送信する。
    """

    def __init__(self, websocket: WebSocketServerProtocol) -> None:
        self._websocket = websocket
        self._pending: dict[str, asyncio.Future[dict[str, Any]]] = {}

    async def run_command(self, command: str, timeout: float = 5.0) -> dict[str, Any]:
        """任意のコマンドを実行し、レスポンスを返す。

        Args:
            command: `/` を含まないコマンド文字列 (例: "setblock 0 64 0 stone")
            timeout: レスポンス待ちのタイムアウト秒数

        Returns:
            Minecraft から返ってきた JSON ボディ
        """
        request_id = str(uuid.uuid4())
        envelope = {
            "header": {
                "version": 1,
                "requestId": request_id,
                "messageType": "commandRequest",
                "messagePurpose": "commandRequest",
            },
            "body": {
                "version": 1,
                "commandLine": command,
                "origin": {"type": "player"},
            },
        }

        future: asyncio.Future[dict[str, Any]] = asyncio.get_event_loop().create_future()
        self._pending[request_id] = future

        await self._websocket.send(json.dumps(envelope))
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        finally:
            self._pending.pop(request_id, None)

    def resolve(self, request_id: str, body: dict[str, Any]) -> None:
        """受信メッセージに対応する pending future を解決する。"""
        future = self._pending.get(request_id)
        if future and not future.done():
            future.set_result(body)

    # --- 高頻度コマンドのヘルパー ---

    async def setblock(self, x: int, y: int, z: int, block: str) -> dict[str, Any]:
        return await self.run_command(f"setblock {x} {y} {z} {block}")

    async def fill(
        self,
        x1: int,
        y1: int,
        z1: int,
        x2: int,
        y2: int,
        z2: int,
        block: str,
    ) -> dict[str, Any]:
        return await self.run_command(f"fill {x1} {y1} {z1} {x2} {y2} {z2} {block}")

    async def say(self, message: str) -> dict[str, Any]:
        return await self.run_command(f'say {message}')


class MinecraftServer:
    """WebSocket サーバー本体。接続中の MinecraftClient を保持する。

    Minecraft は通常 1 セッションしか `/connect` しないため、
    シンプルに「最新の接続」を current として保持する。
    """

    def __init__(self, host: str = "localhost", port: int = 8000) -> None:
        self.host = host
        self.port = port
        self._current: MinecraftClient | None = None
        self._on_chat_handlers: list = []

    @property
    def current(self) -> MinecraftClient | None:
        return self._current

    def on_chat(self, handler):
        """チャットメッセージ受信時のハンドラを登録する。"""
        self._on_chat_handlers.append(handler)
        return handler

    async def _handle_connection(self, websocket: WebSocketServerProtocol) -> None:
        client = MinecraftClient(websocket)
        self._current = client
        logger.info("Minecraft connected: %s", websocket.remote_address)

        # チャットイベントを購読
        subscribe = {
            "header": {
                "version": 1,
                "requestId": str(uuid.uuid4()),
                "messageType": "commandRequest",
                "messagePurpose": "subscribe",
            },
            "body": {"eventName": "PlayerMessage"},
        }
        await websocket.send(json.dumps(subscribe))

        try:
            async for raw in websocket:
                await self._dispatch(client, raw)
        except websockets.ConnectionClosed:
            logger.info("Minecraft disconnected")
        finally:
            if self._current is client:
                self._current = None

    async def _dispatch(self, client: MinecraftClient, raw: str | bytes) -> None:
        try:
            msg = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON: %s", raw)
            return

        header = msg.get("header", {})
        body = msg.get("body", {})
        purpose = header.get("messagePurpose")

        if purpose == "commandResponse":
            client.resolve(header.get("requestId", ""), body)
        elif purpose == "event" and body.get("eventName") == "PlayerMessage":
            message = body.get("properties", {}).get("Message", "")
            sender = body.get("properties", {}).get("Sender", "")
            for handler in self._on_chat_handlers:
                await handler(client, sender, message)

    async def serve(self) -> None:
        """サーバーを起動し、永続的に待ち受ける。"""
        async with websockets.serve(self._handle_connection, self.host, self.port):
            logger.info("WebSocket server listening on ws://%s:%d", self.host, self.port)
            await asyncio.Future()  # forever
