import pydirectinput
import time
import configparser


import utils
from ocr.ocr_service import OCRContext, get_change_btn_position, check_if_have_keyword
from ocr.ocr_enum import FishingLocation
from ocr.ocr_engine import RapidOCREngine
from ocr.ocr_utils import build_pos_by_bounds
from utils import Rect, DxCameraCapture


CAST_HOLD_SECONDS = 0.38
CHANGE_LOCATION_POLL_DELAY_SECONDS = 5.0
CHANGE_LOCATION_POLL_TOTAL_SECONDS = 10
CHANGE_LOCATION_BTN_NAME = "更改"


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
    pydirectinput.keyDown("space")
    time.sleep(CAST_HOLD_SECONDS)
    pydirectinput.keyUp("space")
    print(">>> 抛竿完成")
    
    
def recover_from_timeout(region) -> None:
    pydirectinput.keyDown("up")
    time.sleep(2)
    pydirectinput.keyUp("up")

    center_x, center_y = region.center
    pydirectinput.moveTo(center_x, center_y)
    time.sleep(0.2)
    pydirectinput.click()
    cast_rod()
    
    
def clear_backpack(region: Rect, config: configparser.ConfigParser) -> None:
    print(">>> 清理背包")
    pydirectinput.press("t")
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "one_click_sale_left"), top_ratio=utils.read_config_float(config, "backpack", "one_click_sale_top"), delay=1)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "select_all_left"), top_ratio=utils.read_config_float(config, "backpack", "select_all_top"), delay=1)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "circle_check_left"), top_ratio=utils.read_config_float(config, "backpack", "circle_check_top"))
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "dialog_confirm_left"), top_ratio=utils.read_config_float(config, "backpack", "dialog_confirm_top"), delay=0.5)
    click_button(region=region, left_ratio=utils.read_config_float(config, "backpack", "quit_backpack_left"), top_ratio=utils.read_config_float(config, "backpack", "quit_backpack_top"), delay=0.5) 
    
    
def click_button(region: Rect, left_ratio: float, top_ratio: float, *, delay: float = 0) -> None:
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
    btn_ocr_result = get_change_btn_position(sct, ocr_context, change_location_keyword=CHANGE_LOCATION_BTN_NAME)
    if btn_ocr_result is None or btn_ocr_result.box is None:
        # 如果没有识别到更换按钮，默认点击一个位置
        click_button(region=ocr_context.regions.map, left_ratio=0.21, top_ratio=0.10, delay=0.5)   
    else:
        change_btn_pos = build_pos_by_bounds(btn_ocr_result.box.bounds, ocr_context.regions.location)
        pydirectinput.moveTo(*change_btn_pos)
        pydirectinput.click()
        

def change_location(sct: DxCameraCapture, ocr_context: OCRContext, current_location: FishingLocation) -> None:
    print(">>> 切换钓点")
    
    # 检测更改按钮并点击
    click_change_btn(sct, ocr_context)
    
    # 获取临时地图
    temp_map = MAP_TRANSITIONS.get(current_location, [])[0]
    
    # 点击临时地图按钮
    temp_ratio = temp_map["position"]
    temp_name = temp_map["name"]
    click_button(region=ocr_context.regions.map, left_ratio=temp_ratio[0], top_ratio=temp_ratio[1], delay=2)
        
    # 点击启航按钮
    click_button(region=ocr_context.regions.map, left_ratio=0.85, top_ratio=0.95, delay=0.5)
    
    # 点击确认按钮
    click_button(region=ocr_context.regions.map, left_ratio=0.50, top_ratio=0.58, delay=1)

    # 检测更改按钮并点击
    time.sleep(CHANGE_LOCATION_POLL_DELAY_SECONDS)
    click_change_btn(sct, ocr_context)

    # 从临时地图继续查找回目标地点的路径并点击
    for next_map in MAP_TRANSITIONS.get(temp_name, []):
        if next_map.get("name") != current_location:
            continue

        next_ratio = next_map["position"]
        click_button(region=ocr_context.regions.map, left_ratio=next_ratio[0], top_ratio=next_ratio[1], delay=0.5)
        break
    
    # 点击启航按钮
    click_button(region=ocr_context.regions.map, left_ratio=0.85, top_ratio=0.95, delay=0.5)
    
    # 点击确认按钮
    click_button(region=ocr_context.regions.map, left_ratio=0.50, top_ratio=0.58, delay=1)
    
    # 检测是否成功切换地点
    time.sleep(CHANGE_LOCATION_POLL_DELAY_SECONDS)
    now = time.monotonic()
    while time.monotonic() - now < CHANGE_LOCATION_POLL_TOTAL_SECONDS:
        if check_if_have_keyword(sct, ocr_context, CHANGE_LOCATION_BTN_NAME):
            print(">>> 已成功切换地点")
            return
    

    
    
        
    
    
    
