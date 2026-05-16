"""Registry の基本動作テスト。"""

from __future__ import annotations

from mc_bedrock_mcp.registry import (
    all_builders,
    get,
    load_builtin_builders,
    to_mcp_tool_schema,
)


def test_load_builtin_builders():
    load_builtin_builders()
    names = {b.name for b in all_builders()}
    assert "tower" in names
    assert "pyramid" in names
    assert "sphere" in names


def test_mcp_schema_generation():
    load_builtin_builders()
    entry = get("tower")
    assert entry is not None
    schema = to_mcp_tool_schema(entry)
    assert schema["name"] == "mc_build_tower"
    props = schema["inputSchema"]["properties"]
    assert props["height"]["type"] == "integer"
    assert props["block"]["type"] == "string"
    # デフォルト値がある引数は required に含まれない
    assert "height" not in schema["inputSchema"]["required"]
