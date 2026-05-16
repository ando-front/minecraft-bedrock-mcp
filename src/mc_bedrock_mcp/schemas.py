"""共通データモデル。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class Position(BaseModel):
    """ワールド座標。"""

    x: int
    y: int
    z: int


class BlockRegion(BaseModel):
    """直方体領域。"""

    p1: Position
    p2: Position
    block: str = Field(default="stone", description="Minecraft block id (e.g. 'stone', 'diamond_block')")
