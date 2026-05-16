"""球体を建てるサンプル builder。"""

from __future__ import annotations

from ..mc import MinecraftClient
from ..registry import builder


@builder("sphere")
async def sphere(
    mc: MinecraftClient,
    radius: int = 8,
    block: str = "glass",
    x: int = 0,
    y: int = 80,
    z: int = 0,
    hollow: bool = True,
) -> str:
    """中空または中実の球体を建てる。

    Args:
        radius: 球の半径
        block: 使用するブロック ID
        x, y, z: 球の中心座標
        hollow: True なら外殻のみ、False なら中実
    """
    count = 0
    r2 = radius * radius
    inner2 = (radius - 1) * (radius - 1)
    for dx in range(-radius, radius + 1):
        for dy in range(-radius, radius + 1):
            for dz in range(-radius, radius + 1):
                d2 = dx * dx + dy * dy + dz * dz
                if d2 > r2:
                    continue
                if hollow and d2 < inner2:
                    continue
                await mc.setblock(x + dx, y + dy, z + dz, block)
                count += 1
    return f"Built sphere: radius={radius}, blocks={count}, hollow={hollow}"
