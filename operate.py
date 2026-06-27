"""封装抛竿、背包清理和钓点切换等会操作游戏界面的动作。"""

import pydirectinput
import time
import configparser


import utils
from ocr.ocr_service import OCRContext, get_change_btn_position, check_if_have_keyword, detect_location_from_ocr
from ocr.ocr_enum import FishingLocation
from ocr.ocr_engine import RapidOCREngine
from ocr.ocr_utils import build_pos_by_bounds
from utils import Rect, DxCameraCapture


CAST_HOLD_SECONDS = 0.38
CHANGE_LOCATION_POLL_DELAY_SECONDS = 5.0
CHANGE_LOCATION_POLL_TOTAL_SECONDS = 10
CHANGE_LOCATION_BTN_NAME = "更改"
DEFAULT_BACKPACK_BUTTON_CLICK_INTERVAL_SECONDS = 2.0


MAP_TRANSITIONS = {
    FishingLocation.YANBO_LAKE: [
        {"name": FishingLocation.SHALLOW_SHORE, "position": (0.39, 0.53)},
        {"name": FishingLocation.FROST_STRAIT, "position": (0.29, 0.30)},
        {"name": FishingLocation.ABYSS_MAW, "position": (0.01, 0.48)},
        {"name": FishingLocation.ATLANTIS, "position": (0.01, 0.48)},
    ],
    FishingLocation.SHALLOW_SHORE: [
        {"name": FishingLocation.YANBO_LAKE, "position": (0.41, 0.79)}
    ],
    FishingLocation.FROST_STRAIT: [
        {"name": FishingLocation.YANBO_LAKE, "position": (0.48, 0.79)}
    ],
    FishingLocation.ABYSS_MAW: [
        {"name": FishingLocation.YANBO_LAKE, "position": (0.60, 0.79)}
    ],
    FishingLocation.ATLANTIS: [
        {"name": FishingLocation.YANBO_LAKE, "position": (0.60, 0.79)}
    ]
}


def cast_rod() -> None:
    """按住空格指定时长完成一次抛竿。"""
    pydirectinput.keyDown("space")
    time.sleep(CAST_HOLD_SECONDS)
    pydirectinput.keyUp("space")
    print(">>> 抛竿完成")
    
    
def recover_from_timeout(region) -> None:
    """等待上钩超时后移动角色并点击画面，使游戏回到可抛竿状态。"""
    pydirectinput.keyDown("up")
    time.sleep(2)
    pydirectinput.keyUp("up")

    center_x, center_y = region.center
    pydirectinput.moveTo(center_x, center_y)
    time.sleep(0.2)
    pydirectinput.click()
    cast_rod()
    
    
def clear_backpack(
    region: Rect,
    config: configparser.ConfigParser,
    sct: DxCameraCapture | None = None,
    ocr_context: OCRContext | None = None,
) -> None:
    """执行背包出售流程；退出后若地点 OCR 消失则重试一次。"""
    print(">>> 清理背包")
    button_click_interval = _click_clear_backpack_buttons(region, config)
    if not _should_retry_clear_backpack(sct, ocr_context, button_click_interval):
        return

    print(">>> 清理背包后未检测到钓鱼地点，再次清理背包")
    _click_clear_backpack_buttons(region, config, open_backpack=False)


def _click_clear_backpack_buttons(
    region: Rect,
    config: configparser.ConfigParser,
    *,
    open_backpack: bool = True,
) -> float:
    """按配置坐标依次点击背包按钮，并返回按钮间隔供后续验证使用。"""
    button_click_interval = config.getfloat(
        "backpack",
        "button_click_interval_seconds",
        fallback=DEFAULT_BACKPACK_BUTTON_CLICK_INTERVAL_SECONDS,
    )
    if open_backpack:
        pydirectinput.press("t")
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "one_click_sale_left"), top_ratio=utils.read_config_float(config, "backpack", "one_click_sale_top"), delay=button_click_interval)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "select_all_left"), top_ratio=utils.read_config_float(config, "backpack", "select_all_top"), delay=button_click_interval)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "circle_check_left"), top_ratio=utils.read_config_float(config, "backpack", "circle_check_top"), delay=button_click_interval)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "dialog_confirm_left"), top_ratio=utils.read_config_float(config, "backpack", "dialog_confirm_top"), delay=button_click_interval)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "quit_backpack_left"), top_ratio=utils.read_config_float(config, "backpack", "quit_backpack_top"), delay=button_click_interval) 
    return button_click_interval


def _should_retry_clear_backpack(
    sct: DxCameraCapture | None,
    ocr_context: OCRContext | None,
    check_delay: float,
) -> bool:
    """仅在 OCR 可用且退出背包后看不到地点时要求重试。"""
    if sct is None or ocr_context is None:
        return False

    if not ocr_context.enabled or ocr_context.engine is None:
        return False

    if check_delay:
        time.sleep(check_delay)

    return detect_location_from_ocr(sct, ocr_context, auto_select_strategy=True) is None
    
    
def click_button(region: Rect, left_ratio: float, top_ratio: float, *, delay: float = 0) -> None:
    """把相对区域比例换算成屏幕坐标后点击。"""
    if delay:
        time.sleep(delay)
    pos = utils.build_point_from_ratio(
        region,
        left_ratio=left_ratio,
        top_ratio=top_ratio,
    )
    pydirectinput.moveTo(*pos)
    pydirectinput.click()


def click_change_btn(sct: DxCameraCapture, ocr_context: OCRContext) -> None:
    """点击 OCR 识别到的“更改”按钮，识别失败时使用已知兜底坐标。"""
    btn_ocr_result = get_change_btn_position(sct, ocr_context, change_location_keyword=CHANGE_LOCATION_BTN_NAME)
    if btn_ocr_result is None or btn_ocr_result.box is None:
        # 按钮文字偶尔会被动画遮挡，兜底坐标仍位于固定的“更改”按钮区域。
        click_button(region=ocr_context.regions.map, left_ratio=0.21, top_ratio=0.10, delay=0.5)   
    else:
        change_btn_pos = build_pos_by_bounds(btn_ocr_result.box.bounds, ocr_context.regions.location)
        pydirectinput.moveTo(*change_btn_pos)
        pydirectinput.click()
        

def change_location(sct: DxCameraCapture, ocr_context: OCRContext, current_location: FishingLocation) -> None:
    """先前往中转钓点，再按反向路径回到当前钓点以刷新鱼群。"""
    print(">>> 切换钓点")
    
    # 先从当前地点前往中转点，让原地点在返回时重新加载。
    click_change_btn(sct, ocr_context)
    
    # 每个钓点的第一条边指向中转点，当前地图结构以烟波湖为中心。
    temp_map = MAP_TRANSITIONS.get(current_location, [])[0]
    
    temp_ratio = temp_map["position"]
    temp_name = temp_map["name"]
    click_button(region=ocr_context.regions.map, left_ratio=temp_ratio[0], top_ratio=temp_ratio[1], delay=2)
        
    click_button(region=ocr_context.regions.map, left_ratio=0.85, top_ratio=0.95, delay=0.5)
    
    click_button(region=ocr_context.regions.map, left_ratio=0.50, top_ratio=0.58, delay=1)

    # 到达中转点后重新打开地图，沿反向边回到原地点。
    time.sleep(CHANGE_LOCATION_POLL_DELAY_SECONDS)
    click_change_btn(sct, ocr_context)

    # 从临时地图继续查找回目标地点的路径并点击
    for next_map in MAP_TRANSITIONS.get(temp_name, []):
        if next_map.get("name") != current_location:
            continue

        next_ratio = next_map["position"]
        click_button(region=ocr_context.regions.map, left_ratio=next_ratio[0], top_ratio=next_ratio[1], delay=0.5)
        break
    
    click_button(region=ocr_context.regions.map, left_ratio=0.85, top_ratio=0.95, delay=0.5)
    
    click_button(region=ocr_context.regions.map, left_ratio=0.50, top_ratio=0.58, delay=1)
    
    # “更改”按钮重新出现表示航行动画结束且地图界面恢复可操作。
    time.sleep(CHANGE_LOCATION_POLL_DELAY_SECONDS)
    now = time.monotonic()
    while time.monotonic() - now < CHANGE_LOCATION_POLL_TOTAL_SECONDS:
        if check_if_have_keyword(sct, ocr_context, CHANGE_LOCATION_BTN_NAME):
            print(">>> 已成功切换地点")
            return
    

    
    
        
    
    
    
