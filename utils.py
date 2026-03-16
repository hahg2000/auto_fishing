from __future__ import annotations

import configparser
import os
import sys

import cv2
import numpy as np
import win32gui

def get_client_region(hwnd: int) -> dict[str, int] | None:
    # 按窗口标题获取窗口区域
    if not hwnd:
        return None
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    client_left, client_top = win32gui.ClientToScreen(hwnd, (left, top))
    client_right, client_bottom = win32gui.ClientToScreen(hwnd, (right, bottom))
    return {
        "left": client_left,
        "top": client_top,
        "width": client_right - client_left,
        "height": client_bottom - client_top,
    }
    
def get_pure_game_frame(hwnd, raw_frame_bgra):
    """
    将包含标题栏的原始窗口截图，精准裁切为纯游戏画面
    :param hwnd: 游戏窗口句柄
    :param raw_frame_bgra: windows_capture 返回的 numpy 数组
    :return: 纯游戏画面的 numpy 数组
    """
    # 1. 获取包含边框和标题栏的整个窗口的坐标 (左, 上, 右, 下)
    win_rect = win32gui.GetWindowRect(hwnd)
    
    # 2. 获取纯游戏内部区域的大小 (0, 0, 宽度, 高度)
    client_rect = win32gui.GetClientRect(hwnd)
    
    # 3. 计算客户区左上角在屏幕上的绝对坐标
    # 把客户区的 (0,0) 转换成屏幕上的物理坐标
    client_point = win32gui.ClientToScreen(hwnd, (0, 0))
    
    # 4. 计算偏移量 (核心逻辑)
    # 左边框宽度 = 客户区左边缘 X - 窗口左边缘 X
    border_left = client_point[0] - win_rect[0]
    
    # 标题栏高度 = 客户区顶边缘 Y - 窗口顶边缘 Y
    title_bar_top = client_point[1] - win_rect[1]
    
    # 5. 计算要保留的区域边界
    # 图像总高度和总宽度 (基于 capture 返回的实际画面，防越界)
    img_h, img_w = raw_frame_bgra.shape[:2]
    
    # 纯游戏的实际宽度和高度
    client_w = client_rect[2]
    client_h = client_rect[3]
    
    # 6. 对 NumPy 数组进行精准切片 (剔除四周杂边)
    # 格式: img[上边界 : 下边界, 左边界 : 右边界]
    pure_game_frame = raw_frame_bgra[
        title_bar_top : title_bar_top + client_h,
        border_left : border_left + client_w
    ]
    
    return pure_game_frame


def get_resource_path(relative_path: str) -> str:
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path) # type: ignore
    return os.path.join(os.path.abspath("."), relative_path)


def read_ini(filename: str = "config.ini") -> configparser.ConfigParser:
    # 兼容脚本运行与 PyInstaller 打包运行
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    full_path = os.path.join(base_path, filename)
    print(f">>> Loading config: {full_path}")

    config = configparser.ConfigParser()
    if not os.path.exists(full_path):
        print(f">>> Config not found, creating default file: {full_path}")
        with open(full_path, "w", encoding="utf-8-sig") as file:
            file.write(DEFAULT_CONFIG_CONTENT)

    config.read(full_path, encoding="utf-8-sig")
    return config


def read_config_int(config: configparser.ConfigParser, section: str, key: str) -> int:
    return int(config[section][key])


def read_config_float(
    config: configparser.ConfigParser,
    section: str,
    key: str,
    default: float,
) -> float:
    if not config.has_option(section, key):
        return default
    try:
        return float(config.get(section, key))
    except ValueError:
        return default


def read_config_bool(
    config: configparser.ConfigParser,
    section: str,
    key: str,
    default: bool = False,
) -> bool:
    if not config.has_option(section, key):
        return default
    value = config.get(section, key).strip().lower()
    return value in ("1", "true", "yes", "on", "y")


def readConfigAndCastInt(config: configparser.ConfigParser, section: str, key: str) -> int:
    # 兼容旧调用
    return read_config_int(config, section, key)


def crop_frame(frame: np.ndarray, box: list[int]) -> np.ndarray:
    """
    将包含标题栏的原始窗口截图，精准裁切为纯游戏画面
    
    Parameters:
        frame - 原始窗口截图
        box - [top_percent, bottom_percent, left_percent, right_percent] 百分比裁剪区域

    """
    top, bottom, left, right = box
    h, w = frame.shape[:2]
    y_start = int(h * top / 100)
    y_end = int(h * bottom / 100)
    x_start = int(w * left / 100)
    x_end = int(w * right / 100)
    return frame[y_start:y_end, x_start:x_end]


def to_bgr(image: np.ndarray) -> np.ndarray:
    # 统一成 BGR，兼容 BGRA 输入
    if image.ndim != 3:
        raise ValueError("Image must be BGR or BGRA.")
    if image.shape[2] == 3:
        return image
    if image.shape[2] == 4:
        return cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
    raise ValueError(f"Unsupported channel count: {image.shape[2]}")


def to_hsv(image: np.ndarray) -> np.ndarray:
    # 先转 BGR 再转 HSV，避免 BGRA 直接转换带来的偏差
    return cv2.cvtColor(to_bgr(image), cv2.COLOR_BGR2HSV)


def create_color_mask(
    lower_color: np.ndarray | list[int],
    upper_color: np.ndarray | list[int],
    roi_hsv: np.ndarray,
    is_dilate: bool = True,
) -> np.ndarray:
    lower = np.array(lower_color)
    upper = np.array(upper_color)
    mask = cv2.inRange(roi_hsv, lower, upper)
    if is_dilate:
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


def relative_point(region: dict[str, int], x_ratio: float, y_ratio: float) -> tuple[int, int]:
    x = int(region["left"] + region["width"] * x_ratio / 100)
    y = int(region["top"] + region["height"] * y_ratio / 100)
    return (x, y)


def window_center(region: dict[str, int]) -> tuple[int, int]:
    return (
        region["left"] + region["width"] // 2,
        region["top"] + region["height"] // 2,
    )

DEFAULT_CONFIG_CONTENT = """[hook]
; Hook alert ROI
top_percent = 31
bottom_percent = 40
left_percent = 49
right_percent = 51

hook_lower_yellow_hue = 20
hook_lower_yellow_saturation = 35
hook_lower_yellow_value = 210
hook_upper_yellow_hue = 30
hook_upper_yellow_saturation = 120
hook_upper_yellow_value = 255

[roi]
; qte位置
top_percent = 85
bottom_percent = 89
left_percent = 39
right_percent = 65

; 倒计时位置
time_top_percent = 80
time_bottom_percent = 90
time_left_percent = 32
time_right_percent = 38

; 倒计时绿色颜色区间
time_lower_green_hue = 65
time_lower_green_saturation = 185
time_lower_green_value = 210
time_upper_green_hue = 75
time_upper_green_saturation = 195
time_upper_green_value = 255

; 倒计时红色颜色区间
time_lower_red_hue = 170
time_lower_red_saturation = 155
time_lower_red_value = 240
time_upper_red_hue = 180
time_upper_red_saturation = 170
time_upper_red_value = 255

; 黄色颜色区间
lower_yellow_hue = 20
lower_yellow_saturation = 100
lower_yellow_value = 185
upper_yellow_hue = 30
upper_yellow_saturation = 255
upper_yellow_value = 255

; 红色颜色区间
lower_red_hue = 170
lower_red_saturation = 100
lower_red_value = 100
upper_red_hue = 180
upper_red_saturation = 255
upper_red_value = 255

; 绿色颜色区间
lower_green_hue = 59
lower_green_saturation = 95
lower_green_value = 209
upper_green_hue = 75
upper_green_saturation = 163
upper_green_value = 234

; 蓝色颜色区间
lower_blue_hue = 95
lower_blue_saturation = 105
lower_blue_value = 255
upper_blue_hue = 102
upper_blue_saturation = 255
upper_blue_value = 255

; 白色颜色区间
lower_white_hue = 0
lower_white_saturation = 0
lower_white_value = 240
upper_white_hue = 180
upper_white_saturation = 50
upper_white_value = 255

[backpack]
; 一键出售按钮位置
one_click_sale_left = 0.87
one_click_sale_top = 0.92

; 全选按钮位置
select_all_left = 0.82
select_all_top = 0.92

; 圆形打钩按钮位置
circle_check_left = 0.92
circle_check_top = 0.92

; 提示框确定按钮位置
dialog_confirm_left = 0.57
dialog_confirm_top = 0.61

; 退出背包位置
quit_backpack_left = 0.1
quit_backpack_top = 0.12

[time]
; 一轮钓鱼结束后等待的时间，根据网络情况可以调整
round_end_wait_time = 2

; 钓鱼成功后的停留时间，来等待动画效果结束，根据电脑情况可以调整
fish_end_wait_time = 2

; 执行脚本后的停留时间，来预留时间能切换到游戏界面
begin_fish_wait_time = 3

; 钓鱼的最长持续时间，用于防止错误一直退出不了qte时刻
longest_keep_time = 35
wait_bite_timeout = 12

[debug]
enable = 0
show_windows = 1
stats_interval = 1.0
"""
