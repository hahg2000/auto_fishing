"""集中定义钓鱼地点以及 OCR 容错匹配所需的文字别名。"""

from __future__ import annotations

from enum import StrEnum
from typing import Final


class FishingLocation(StrEnum):
    """游戏内支持的钓鱼地点；枚举值与界面中文名称一致。"""

    YANBO_LAKE = "烟波湖"
    SHALLOW_SHORE = "浅岸"
    FROST_STRAIT = "寒霜海峡"
    ABYSS_MAW = "深渊巨口"
    ATLANTIS = "亚特兰蒂斯"


DEFAULT_LOCATION: Final[FishingLocation] = FishingLocation.YANBO_LAKE

LOCATION_MATCH_ALIASES: Final[dict[FishingLocation, tuple[str, ...]]] = {
    FishingLocation.YANBO_LAKE: ("烟波湖", "烟波"),
    FishingLocation.SHALLOW_SHORE: ("浅岸",),
    FishingLocation.FROST_STRAIT: ("寒霜海峡", "寒霜海", "寒霜"),
    FishingLocation.ABYSS_MAW: ("深渊巨口", "深渊", "巨口"),
    FishingLocation.ATLANTIS: ("亚特兰蒂斯", "亚特兰蒂", "特兰蒂斯"),
}

BACKPACK_FULL_MATCH_ALIASES: tuple[str, ...] = (
    "背包已满，请清理背包",
    "背包已满请清理背包",
    "背包已满",
    "请清理背包",
    "清理背包",
)
