"""ピラミッドを建てるサンプル builder。"""

from __future__ import annotations

from ..mc import MinecraftClient
from ..registry import builder


@builder("pyramid")
async def pyramid(
    mc: MinecraftClient,
    size: int = 10,
    block: str = "sandstone",
    x: int = 0,
    y: int = 64,
    z: int = 0,
) -> str:
    """指定サイズのピラミッドを建てる。

    Args:
        size: ピラミッドの底辺の半径 (実際の底辺は 2*size+1)
        block: 使用するブロック ID
        x, y, z: ピラミッド中心の底面座標
    """
    for layer in range(size + 1):
        r = size - layer
        await mc.fill(x - r, y + layer, z - r, x + r, y + layer, z + r, block)
    return f"Built pyramid: size={size}, block={block}, center=({x},{y},{z})"
