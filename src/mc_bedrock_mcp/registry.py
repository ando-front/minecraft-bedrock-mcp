"""Builder 関数のレジストリ。

`@builder("name")` を付けた関数を中央レジストリに登録し、
- チャットコマンド層からの名前ベース呼び出し
- MCP tool としての JSON Schema 自動生成

の両方を可能にする。新しい builder の追加は `builders/` 配下に
ファイルを追加するだけで完結し、既存コードの変更は不要。
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .mc import MinecraftClient

BuilderFunc = Callable[..., Awaitable[Any]]


@dataclass
class BuilderEntry:
    name: str
    func: BuilderFunc
    doc: str
    signature: inspect.Signature


_registry: dict[str, BuilderEntry] = {}


def builder(name: str) -> Callable[[BuilderFunc], BuilderFunc]:
    """Builder 関数を登録するデコレータ。

    関数の第一引数は MinecraftClient であることを期待する。
    型ヒントとデフォルト値から MCP tool のスキーマが自動生成される。
    """

    def decorator(func: BuilderFunc) -> BuilderFunc:
        sig = inspect.signature(func)
        doc = inspect.getdoc(func) or f"Build {name}."
        _registry[name] = BuilderEntry(name=name, func=func, doc=doc, signature=sig)
        return func

    return decorator


def get(name: str) -> BuilderEntry | None:
    return _registry.get(name)


def all_builders() -> list[BuilderEntry]:
    return list(_registry.values())


def load_builtin_builders() -> None:
    """`builders` パッケージ配下のモジュールを全て import して登録を発火させる。"""
    from . import builders as builders_pkg

    for _, modname, _ in pkgutil.iter_modules(builders_pkg.__path__):
        importlib.import_module(f"{builders_pkg.__name__}.{modname}")


# --- MCP tool schema 生成 ---

_PY_TO_JSON_TYPE = {
    int: "integer",
    float: "number",
    str: "string",
    bool: "boolean",
}


def to_mcp_tool_schema(entry: BuilderEntry) -> dict[str, Any]:
    """Builder の signature を MCP tool スキーマに変換する。

    第一引数 (MinecraftClient) は除外し、残りを inputSchema として公開する。
    """
    properties: dict[str, Any] = {}
    required: list[str] = []

    params = list(entry.signature.parameters.values())
    # 第一引数は MinecraftClient なのでスキップ
    for param in params[1:]:
        annotation = param.annotation
        json_type = _PY_TO_JSON_TYPE.get(annotation, "string")
        properties[param.name] = {"type": json_type}
        if param.default is inspect.Parameter.empty:
            required.append(param.name)
        else:
            properties[param.name]["default"] = param.default

    schema = {
        "name": f"mc_build_{entry.name}",
        "description": entry.doc,
        "inputSchema": {
            "type": "object",
            "properties": properties,
            "required": required,
        },
    }
    return schema


async def invoke(name: str, mc: MinecraftClient, **kwargs: Any) -> Any:
    """登録名から builder を呼び出す。"""
    entry = _registry.get(name)
    if entry is None:
        raise KeyError(f"Builder not found: {name}")
    return await entry.func(mc, **kwargs)
