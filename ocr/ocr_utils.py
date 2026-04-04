import unicodedata
import utils
import os
import configparser

from utils import Rect
from ocr.ocr_engine import RapidOCREngine
from ocr.ocr_enum import FishingLocation, LOCATION_MATCH_ALIASES, BACKPACK_FULL_MATCH_ALIASES
from dataclasses import dataclass


@dataclass(frozen=True)
class OCRRegions:
    location: Rect
    map: Rect
    backpack_full: Rect


@dataclass(frozen=True)
class OCRContext:
    enabled: bool
    engine: RapidOCREngine | None
    regions: OCRRegions


def normalize_ocr_text(text: str) -> str:
    normalized: list[str] = []
    for char in text:
        if char.isspace():
            continue
        category = unicodedata.category(char)
        if category.startswith("P") or category.startswith("S"):
            continue
        normalized.append(char.lower())
    return "".join(normalized)


def build_normalized_ocr_candidates(texts: list[str]) -> list[str]:
    normalized_candidates: list[str] = []
    for text in texts:
        normalized_text = normalize_ocr_text(text)
        if normalized_text:
            normalized_candidates.append(normalized_text)

    merged_candidate = normalize_ocr_text("".join(texts))
    if merged_candidate:
        normalized_candidates.append(merged_candidate)

    return normalized_candidates
  
    
def has_alias_match(normalized_candidates: list[str], aliases: tuple[str, ...]) -> bool:
    for alias in aliases:
        normalized_alias = normalize_ocr_text(alias)
        if not normalized_alias:
            continue
        for candidate in normalized_candidates:
            if normalized_alias in candidate:
                return True
            if len(candidate) >= 2 and candidate in normalized_alias:
                return True
    return False

    
def sort_ocr_results(results: list) -> None:
    results.sort(
        key=lambda item: (
            item.box.bounds[1] if item.box is not None else 0,
            item.box.bounds[0] if item.box is not None else 0,
        )
    )

    
def match_location_name(texts: list[str]) -> FishingLocation | None:
    normalized_candidates = build_normalized_ocr_candidates(texts)
    for location_name, aliases in LOCATION_MATCH_ALIASES.items():
        candidate_aliases = (location_name.value, *aliases)
        if has_alias_match(normalized_candidates, candidate_aliases):
            return location_name
    return None


def contains_backpack_full_text(texts: list[str]) -> bool:
    normalized_candidates = build_normalized_ocr_candidates(texts)
    return has_alias_match(normalized_candidates, BACKPACK_FULL_MATCH_ALIASES)


def resolve_ocr_resource_path(config: configparser.ConfigParser, key: str) -> str | None:
    configured_value = config.get("ocr", key, fallback="").strip()
    if not configured_value:
        return None

    resolved_path = utils.get_resource_path(configured_value)
    if os.path.exists(resolved_path):
        return resolved_path

    return None


def build_ocr_engine(config: configparser.ConfigParser) -> RapidOCREngine:
    det_model_path = resolve_ocr_resource_path(config, "det_model_path")
    cls_model_path = resolve_ocr_resource_path(config, "cls_model_path")
    rec_model_path = resolve_ocr_resource_path(config, "rec_model_path")
    rec_keys_path = resolve_ocr_resource_path(config, "rec_keys_path")
    return RapidOCREngine(
        det_model_path=det_model_path,
        cls_model_path=cls_model_path,
        rec_model_path=rec_model_path,
        rec_keys_path=rec_keys_path,
        use_cls=config.getboolean("ocr", "use_cls", fallback=False),
    )


def build_optional_ocr_region(
    config: configparser.ConfigParser,
    region: Rect,
    *,
    left_key: str,
    top_key: str,
    right_key: str,
    bottom_key: str,
) -> Rect:
    if not all(
        config.has_option("ocr", key)
        for key in (left_key, top_key, right_key, bottom_key)
    ):
        left_percent = 0
        top_percent = 0
        right_percent = 100
        bottom_percent = 100
    else:
        left_percent=config.getint("ocr", left_key)
        top_percent=config.getint("ocr", top_key)
        right_percent=config.getint("ocr", right_key)
        bottom_percent=config.getint("ocr", bottom_key)
    return utils.build_region_from_percent(
        region,
        left_percent = left_percent,
        top_percent = top_percent,
        right_percent = right_percent,
        bottom_percent = bottom_percent
    )
    

def build_ocr_context(config: configparser.ConfigParser, region: Rect) -> OCRContext:
    ocr_regions = OCRRegions(
        build_optional_ocr_region(
            config,
            region,
            left_key="location_left_percent",
            top_key="location_top_percent",
            right_key="location_right_percent",
            bottom_key="location_bottom_percent",
        ), build_optional_ocr_region(
            config,
            region,
            left_key="map_left_percent",
            top_key="map_top_percent",
            right_key="map_right_percent",
            bottom_key="map_bottom_percent",
        ), build_optional_ocr_region(
            config,
            region,
            left_key="backpack_full_left_percent",
            top_key="backpack_full_top_percent",
            right_key="backpack_full_right_percent",
            bottom_key="backpack_full_bottom_percent",
        ) 
    )
    
    ocr_enabled = config.getboolean("ocr", "enabled", fallback=False)
    ocr_engine = None
    if ocr_enabled:
        try:
            ocr_engine = build_ocr_engine(config)
        except Exception as exc:
            print(f">>> OCR init failed: {exc}")
            ocr_enabled = False
    
    return OCRContext(
        ocr_enabled,
        ocr_engine,
        ocr_regions,
    )


def build_pos_by_bounds(bounds, region: Rect):
    left, top, right, bottom = bounds

    abs_center_x = region.left + (left + right) // 2
    abs_center_y = region.top + (top + bottom) // 2
    
    return abs_center_x, abs_center_y

