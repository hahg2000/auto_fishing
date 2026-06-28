import time

from ocr.ocr_engine import OCRText, RapidOCREngine
from ocr.ocr_utils import (
    OCRContext,
    FishingLocation,
    contains_backpack_full_text,
    match_location_name,
    sort_ocr_results,
)
from utils import DxCameraCapture, Rect

CHANGE_LOCATION_POLL_TOTAL_SECONDS = 10
CHANGE_LOCATION_POLL_INTERVAL_SECONDS = 1.0


def get_result_from_ocr(
    sct: DxCameraCapture,
    ocr_engine: RapidOCREngine | None,
    ocr_region: Rect,
) -> list[OCRText] | None:
    if ocr_engine is None:
        return None

    frame = sct.grab(ocr_region)
    if frame is None:
        print(">>> OCR 截图失败")
        return None

    try:
        results = ocr_engine.detect_and_recognize(frame)
        return results
    except Exception as exc:
        print(f">>> OCR 执行失败: {exc}")
        return None


def get_result_by_keyword(sct: DxCameraCapture, ocr_engine: RapidOCREngine | None, ocr_region: Rect, keyword: str) -> OCRText | None:
    results = get_result_from_ocr(sct, ocr_engine, ocr_region)

    if results is None:
        return None

    for item in results:
        if keyword == item.text:
            return item

    return None


def get_texts_from_ocr(
    sct: DxCameraCapture,
    ocr_engine: RapidOCREngine | None,
    ocr_region: Rect,
) -> list[str] | None:
    results = get_result_from_ocr(sct, ocr_engine, ocr_region)

    if results is None:
        return None
    sort_ocr_results(results)
    texts = [item.text.strip() for item in results if item.text.strip()]
    return texts


def get_change_btn_position(sct: DxCameraCapture, ocr_context: OCRContext, change_location_keyword: str) -> OCRText | None:
    started_at = time.monotonic()
    while time.monotonic() - started_at < CHANGE_LOCATION_POLL_TOTAL_SECONDS:
        result = get_result_by_keyword(sct, ocr_context.engine, ocr_context.regions.location, change_location_keyword)
        if result is not None:
            return result

        time.sleep(CHANGE_LOCATION_POLL_INTERVAL_SECONDS)

    return None


def detect_location_from_ocr(sct: DxCameraCapture, ocr_context: OCRContext, auto_select_strategy: bool) -> FishingLocation | None:
    if not ocr_context.enabled or not auto_select_strategy:
        return None

    texts = get_texts_from_ocr(sct, ocr_context.engine, ocr_context.regions.location)
    if not texts:
        print(">>> OCR 没有识别到任何文本，无法自动选择策略")
        return None

    matched_location = match_location_name(texts)
    if matched_location is None:
        print(">>> OCR 找到了文本但没有匹配的策略")
        return None

    print(f">>> 已检测到地点: {matched_location}")
    return matched_location


def check_backpack_if_full(sct: DxCameraCapture, ocr_context: OCRContext) -> bool:
    if not ocr_context.enabled or ocr_context.engine is None:
        return False

    texts = get_texts_from_ocr(sct, ocr_context.engine, ocr_context.regions.backpack_full)
    if not texts:
        return False

    if not contains_backpack_full_text(texts):
        return False

    print(">>> 检测到“背包已满，请清理背包”，开始清理背包")
    return True


def check_if_have_keyword(sct: DxCameraCapture, ocr_context: OCRContext, keyword: str) -> bool:
    if not ocr_context.enabled or ocr_context.engine is None:
        return False

    texts = get_texts_from_ocr(sct, ocr_context.engine, ocr_context.regions.map)
    if texts is None:
        print(">>> OCR 没有识别到任何文本")
        return False
    if any(keyword in text for text in texts):
        return True

    return False


def check_if_time_to_change_location(sct: DxCameraCapture, ocr_context: OCRContext) -> bool:
    if not ocr_context.enabled or ocr_context.engine is None:
        return False

    if check_if_have_keyword(sct, ocr_context, "小时"):
        return False

    print(">>> OCR 没有检测到“时”字，可能需要切换钓鱼点")
    return True
