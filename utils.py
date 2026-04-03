from __future__ import annotations

import configparser
import os
import sys
from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np
import win32gui


@dataclass(frozen=True)
class Rect:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top

    @property
    def center(self) -> tuple[int, int]:
        return (self.left + self.width // 2, self.top + self.height // 2)

    def as_tuple(self) -> tuple[int, int, int, int]:
        return (self.left, self.top, self.right, self.bottom)


@dataclass(frozen=True)
class HSVRange:
    lower: np.ndarray
    upper: np.ndarray


@dataclass(frozen=True)
class PixelThresholdScale:
    reference_width: int
    reference_height: int
    current_width: int
    current_height: int

    @property
    def factor(self) -> float:
        reference_area = max(1, self.reference_width * self.reference_height)
        current_area = max(1, self.current_width * self.current_height)
        return current_area / reference_area


class DxCameraCapture:
    """对 dxcam 的轻量封装，统一输出 BGR 图像。"""

    def __init__(self, output_color: str = "BGR") -> None:
        import dxcam

        self._camera = dxcam.create(output_color=output_color) # type: ignore

    def grab(self, region: Rect | tuple[int, int, int, int]) -> np.ndarray | None:
        target = region.as_tuple() if isinstance(region, Rect) else region
        frame = self._camera.grab(region=target)
        if frame is None:
            return None
        if frame.ndim == 3 and frame.shape[2] == 4:
            return cv2.cvtColor(frame, cv2.COLOR_BGRA2BGR)
        return frame

    def __enter__(self) -> "DxCameraCapture":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        stop = getattr(self._camera, "stop", None)
        if callable(stop):
            stop()


def get_window_region(window_title: str) -> Rect | None:
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print(f"错误: 未找到标题为 '{window_title}' 的窗口")
        return None

    client_left, client_top = win32gui.ClientToScreen(hwnd, (0, 0))
    client_rect = win32gui.GetClientRect(hwnd)
    client_w = client_rect[2]
    client_h = client_rect[3]

    return Rect(
        left=client_left,
        top=client_top,
        right=client_left + client_w,
        bottom=client_top + client_h,
    )


def get_resource_path(relative_path: str) -> str:
    """获取资源文件的绝对路径。"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path) # type: ignore
    return os.path.join(os.path.abspath("."), relative_path)


def read_ini(filename: str = "config.ini") -> configparser.ConfigParser:
    """读取 ini 配置文件，不存在时自动写入默认配置。"""
    if getattr(sys, "frozen", False):
        base_path = os.path.dirname(sys.executable)
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))

    full_path = os.path.join(base_path, filename)
    print(f">>> 正在读取配置文件路径: {full_path}")

    config = configparser.ConfigParser()
    if not os.path.exists(full_path):
        print(f">>> 配置文件未找到，正在生成默认配置: {full_path}")
        with open(full_path, "w", encoding="utf-8-sig") as file:
            file.write(DEFAULT_CONFIG_CONTENT)

    config.read(full_path, encoding="utf-8-sig")
    return config


def read_config_int(config: configparser.ConfigParser, section: str, key: str) -> int:
    return config.getint(section, key)


def read_config_float(config: configparser.ConfigParser, section: str, key: str) -> float:
    return config.getfloat(section, key)


def read_hsv_range(config: configparser.ConfigParser, section: str, prefix: str) -> HSVRange:
    return read_hsv_range_from_keys(
        config,
        section,
        lower_prefix=f"{prefix}_lower",
        upper_prefix=f"{prefix}_upper",
    )


def read_hsv_range_from_keys(
    config: configparser.ConfigParser,
    section: str,
    *,
    lower_prefix: str,
    upper_prefix: str,
) -> HSVRange:
    lower = np.array(
        [
            read_config_int(config, section, f"{lower_prefix}_hue"),
            read_config_int(config, section, f"{lower_prefix}_saturation"),
            read_config_int(config, section, f"{lower_prefix}_value"),
        ]
    )
    upper = np.array(
        [
            read_config_int(config, section, f"{upper_prefix}_hue"),
            read_config_int(config, section, f"{upper_prefix}_saturation"),
            read_config_int(config, section, f"{upper_prefix}_value"),
        ]
    )
    return HSVRange(lower=lower, upper=upper)


def build_pixel_threshold_scale(
    config: configparser.ConfigParser,
    region: Rect,
) -> PixelThresholdScale:
    reference_width = config.getint("scale", "reference_window_width", fallback=3840)
    reference_height = config.getint("scale", "reference_window_height", fallback=2160)
    return PixelThresholdScale(
        reference_width=reference_width,
        reference_height=reference_height,
        current_width=region.width,
        current_height=region.height,
    )


def scale_pixel_threshold(
    base_threshold: int,
    scale: PixelThresholdScale,
    *,
    minimum: int = 1,
) -> int:
    return max(minimum, int(round(base_threshold * scale.factor)))


def build_region_from_percent(
    window_region: Rect,
    *,
    left_percent: float,
    top_percent: float,
    right_percent: float,
    bottom_percent: float,
) -> Rect:
    return Rect(
        left=window_region.left + int(window_region.width * left_percent / 100),
        top=window_region.top + int(window_region.height * top_percent / 100),
        right=window_region.left + int(window_region.width * right_percent / 100),
        bottom=window_region.top + int(window_region.height * bottom_percent / 100),
    )


def build_region_from_config(
    config: configparser.ConfigParser,
    section: str,
    window_region: Rect,
    *,
    prefix: str = "",
) -> Rect:
    key_prefix = f"{prefix}_" if prefix else ""
    return build_region_from_percent(
        window_region,
        left_percent=read_config_int(config, section, f"{key_prefix}left_percent"),
        top_percent=read_config_int(config, section, f"{key_prefix}top_percent"),
        right_percent=read_config_int(config, section, f"{key_prefix}right_percent"),
        bottom_percent=read_config_int(config, section, f"{key_prefix}bottom_percent"),
    )


def build_point_from_ratio(
    window_region: Rect,
    *,
    left_ratio: float,
    top_ratio: float,
) -> tuple[int, int]:
    return (
        int(window_region.left + window_region.width * left_ratio),
        int(window_region.top + window_region.height * top_ratio),
    )


def create_color_mask(
    lower_color: Iterable[int] | np.ndarray,
    upper_color: Iterable[int] | np.ndarray,
    roi_hsv: np.ndarray,
    *,
    is_dilate: bool = True,
) -> np.ndarray:
    lower = np.array(lower_color)
    upper = np.array(upper_color)
    mask = cv2.inRange(roi_hsv, lower, upper)
    if is_dilate:
        kernel = np.ones((7, 7), np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=2)
    return mask


DEFAULT_CONFIG_CONTENT = """[hook]
; 感叹号位置
top_percent = 25
bottom_percent = 36
left_percent = 49
right_percent = 51

hook_lower_hue = 20
hook_lower_saturation = 35
hook_lower_value = 210
hook_upper_hue = 30
hook_upper_saturation = 120
hook_upper_value = 255

[roi]
; qte位置
top_percent = 80
bottom_percent = 90
left_percent = 32
right_percent = 65

; 倒计时位置
time_top_percent = 0
time_bottom_percent = 100
time_left_percent = 0
time_right_percent = 18

; 倒计时位置
qte_top_percent = 50
qte_bottom_percent = 97
qte_left_percent = 22
qte_right_percent = 100

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
yellow_lower_hue = 20
yellow_lower_saturation = 100
yellow_lower_value = 185
yellow_upper_hue = 30
yellow_upper_saturation = 255
yellow_upper_value = 255

; 红色颜色区间
red_lower_hue = 170
red_lower_saturation = 100
red_lower_value = 100
red_upper_hue = 180
red_upper_saturation = 255
red_upper_value = 255

; 绿色颜色区间
green_lower_hue = 59
green_lower_saturation = 95
green_lower_value = 209
green_upper_hue = 75
green_upper_saturation = 163
green_upper_value = 234

; 蓝色颜色区间
blue_lower_hue = 95
blue_lower_saturation = 105
blue_lower_value = 255
blue_upper_hue = 102
blue_upper_saturation = 255
blue_upper_value = 255

; 白色颜色区间
white_lower_hue = 0
white_lower_saturation = 0
white_lower_value = 240
white_upper_hue = 180
white_upper_saturation = 50
white_upper_value = 255

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

; 热循环的轻量节流时间，减轻 CPU 占用
loop_sleep_seconds = 0.005

; 钓鱼的最长持续时间，用于防止错误一直退出不了qte时刻
longest_keep_time = 35

[scale]
; 像素阈值调试时使用的参考窗口尺寸
reference_window_width = 1152
reference_window_height = 648

[ocr]
; Enable OCR to run once after startup for debugging the target text area.
enabled = true
debug_once_on_start = true
auto_select_strategy = true
location_left_percent = 11
location_top_percent = 8
location_right_percent = 28
location_bottom_percent = 15
use_cls = false
; Leave model paths blank to use RapidOCR package builtin models.
det_model_path =
cls_model_path =
rec_model_path =
rec_keys_path =
"""
