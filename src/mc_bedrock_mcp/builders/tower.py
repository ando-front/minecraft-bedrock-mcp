"""塔を建てるサンプル builder。"""

from __future__ import annotations

from ..mc import MinecraftClient
from ..registry import builder


@builder("tower")
async def tower(
    mc: MinecraftClient,
    height: int = 20,
    block: str = "stone",
    x: int = 0,
    y: int = 64,
    z: int = 0,
) -> str:
    """指定座標から上方向に塔を建てる。

    Args:
        height: 塔の高さ (ブロック数)
        block: 使用するブロック ID
        x, y, z: 塔の底面の座標
    """
    await mc.fill(x, y, z, x, y + height - 1, z, block)
    return f"Built tower: height={height}, block={block}, base=({x},{y},{z})"
