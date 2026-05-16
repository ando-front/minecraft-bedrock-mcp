"""WebSocket 単独モードのエントリポイント。

Minecraft 内のチャットコマンドで builder を起動する従来モード。
MCP を使わずに動作確認したい場合に使う。
"""

from __future__ import annotations

import asyncio
import inspect
import logging
import shlex

from mc_bedrock_mcp.mc import MinecraftClient, MinecraftServer
from mc_bedrock_mcp.registry import (
    BuilderEntry,
    all_builders,
    get,
    invoke,
    load_builtin_builders,
)

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def _coerce(value: str, annotation: type) -> object:
    if annotation is int:
        return int(value)
    if annotation is float:
        return float(value)
    if annotation is bool:
        return value.lower() in {"true", "1", "yes"}
    return value


def _parse_args(entry: BuilderEntry, tokens: list[str]) -> dict[str, object]:
    """位置引数を builder のキーワード引数に変換する。"""
    params = list(entry.signature.parameters.values())[1:]  # skip MinecraftClient
    kwargs: dict[str, object] = {}
    for param, token in zip(params, tokens, strict=False):
        annotation = param.annotation if param.annotation is not inspect.Parameter.empty else str
        kwargs[param.name] = _coerce(token, annotation)
    return kwargs


async def handle_chat(mc: MinecraftClient, sender: str, message: str) -> None:
    if not message or sender == "":
        return

    tokens = shlex.split(message)
    if not tokens:
        return

    name, *args = tokens

    if name == "help":
        names = ", ".join(b.name for b in all_builders())
        await mc.say(f"Available builders: {names}")
        return

    entry = get(name)
    if entry is None:
        return  # 通常チャットを無視

    try:
        kwargs = _parse_args(entry, args)
        logger.info("Invoke builder=%s kwargs=%s", name, kwargs)
        result = await invoke(name, mc, **kwargs)
        await mc.say(str(result))
    except Exception as exc:
        logger.exception("Builder failed")
        await mc.say(f"Error: {exc}")


async def main() -> None:
    load_builtin_builders()
    logger.info("Loaded builders: %s", [b.name for b in all_builders()])

    server = MinecraftServer(host="localhost", port=8000)
    server.on_chat(handle_chat)
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
