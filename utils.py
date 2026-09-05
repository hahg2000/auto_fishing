"""项目通用基础设施：坐标、截图、配置读取、颜色遮罩和阈值缩放。"""

from __future__ import annotations

import configparser
import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from dataclasses import dataclass
from typing import Iterable

import cv2
import numpy as np
import win32gui

@dataclass(frozen=True)
class Rect:
    """使用屏幕绝对坐标表示的左闭右开矩形区域。"""

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
    """OpenCV HSV 颜色范围的上下界。"""

    lower: np.ndarray
    upper: np.ndarray


@dataclass(frozen=True)
class PixelThresholdScale:
    """按当前窗口面积相对参考分辨率缩放像素数量阈值。"""

    reference_width: int
    reference_height: int
    current_width: int
    current_height: int

    @property
    def width_factor(self) -> float:
        """返回当前窗口宽度相对参考窗口宽度的倍率。"""
        return self.current_width / max(1, self.reference_width)

    @property
    def height_factor(self) -> float:
        """返回当前窗口高度相对参考窗口高度的倍率。"""
        return self.current_height / max(1, self.reference_height)

    @property
    def factor(self) -> float:
        """返回当前窗口面积与参考窗口面积之比。"""
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
    """获取窗口客户区的屏幕绝对坐标，不包含标题栏和边框。"""
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


def get_base_path() -> str:
    """返回运行时文件（配置、日志等）应存放的目录。"""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def read_ini(filename: str = "config.ini") -> configparser.ConfigParser:
    """读取 ini 配置文件，不存在时自动写入默认配置。"""
    full_path = os.path.join(get_base_path(), filename)
    print(f">>> 正在读取配置文件路径: {full_path}")

    config = configparser.ConfigParser()
    if not os.path.exists(full_path):
        print(f">>> 配置文件未找到，正在生成默认配置: {full_path}")
        with open(full_path, "w", encoding="utf-8-sig") as file:
            file.write(DEFAULT_CONFIG_CONTENT)

    config.read(full_path, encoding="utf-8-sig")
    return config


def setup_logging() -> None:
    """初始化日志，写入程序目录下的日志文件并输出到控制台。"""
    root_logger = logging.getLogger()
    if root_logger.handlers:
        return
    root_logger.setLevel(logging.DEBUG)

    formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    file_handler = RotatingFileHandler(
        os.path.join(get_base_path(), "auto_fishing.log"),
        maxBytes=5 * 1024 * 1024,
        backupCount=3,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 原生崩溃（如 onnxruntime / dxcam 段错误）时把 Python 调用栈转储到文件。
    try:
        import faulthandler

        fault_file = open(
            os.path.join(get_base_path(), "auto_fishing.fault.log"),
            "w",
            encoding="utf-8",
        )
        faulthandler.enable(file=fault_file)
    except Exception as exc:
        logging.getLogger(__name__).warning("faulthandler 初始化失败: %s", exc)


def install_exception_hook() -> None:
    """捕获未处理异常写入日志，并在打包环境下保持控制台窗口不立即关闭。"""
    logger = logging.getLogger(__name__)

    def handle_uncaught(exc_type, exc_value, exc_tb) -> None:
        if issubclass(exc_type, KeyboardInterrupt):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return
        logger.critical("未捕获的异常", exc_info=(exc_type, exc_value, exc_tb))
        sys.__excepthook__(exc_type, exc_value, exc_tb)
        if getattr(sys, "frozen", False):
            try:
                input(">>> 程序异常退出，详细信息已写入 auto_fishing.log，按回车键关闭")
            except Exception:
                pass

    sys.excepthook = handle_uncaught


def read_config_int(config: configparser.ConfigParser, section: str, key: str) -> int:
    return config.getint(section, key)


def read_config_float(config: configparser.ConfigParser, section: str, key: str) -> float:
    return config.getfloat(section, key)


def read_hsv_range(config: configparser.ConfigParser, section: str, prefix: str) -> HSVRange:
    """按 ``<prefix>_lower/upper_*`` 命名约定读取 HSV 范围。"""
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
    """使用分别指定的上下界前缀读取 HSV 范围。"""
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
    """根据游戏窗口和配置中的参考分辨率创建阈值缩放信息。"""
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
    """按窗口面积缩放像素阈值，并保证结果不低于最小值。"""
    return max(minimum, int(round(base_threshold * scale.factor)))


def scale_pixel_length(
    base_length: int,
    factor: float,
    *,
    minimum: int = 0,
) -> int:
    """按单一方向的缩放倍率换算像素长度。"""
    return max(minimum, int(round(base_length * factor)))


def build_region_from_percent(
    window_region: Rect,
    *,
    left_percent: int,
    top_percent: int,
    right_percent: int,
    bottom_percent: int,
) -> Rect:
    """把窗口内百分比区域转换成屏幕绝对坐标。"""
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
    """从配置节读取百分比区域；可用前缀区分同节中的多个区域。"""
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
    """把区域内的横纵比例转换成屏幕绝对点击坐标。"""
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
    dilate_kernel_size: tuple[int, int] = (7, 7),
    dilate_iterations: int = 2,
) -> np.ndarray:
    """创建 HSV 二值遮罩，并按需膨胀以连接断裂或被遮挡的颜色区域。"""
    lower = np.array(lower_color)
    upper = np.array(upper_color)
    mask = cv2.inRange(roi_hsv, lower, upper)
    if is_dilate:
        # NumPy 核尺寸顺序为（高度, 宽度），迭代次数越多扩张范围越大。
        kernel = np.ones(dilate_kernel_size, np.uint8)
        mask = cv2.dilate(mask, kernel, iterations=dilate_iterations)
    return mask


DEFAULT_CONFIG_CONTENT = """[hook]
; 感叹号位置
top_percent = 25
bottom_percent = 37
left_percent = 49
right_percent = 51

hook_lower_hue = 20
hook_lower_saturation = 35
hook_lower_value = 210
hook_upper_hue = 30
hook_upper_saturation = 120
hook_upper_value = 255

[roi]
; QTE 整体截图区域
top_percent = 82
bottom_percent = 90
left_percent = 32
right_percent = 65

; 倒计时条在整体截图中的相对区域
time_top_percent = 0
time_bottom_percent = 100
time_left_percent = 0
time_right_percent = 18

; QTE 条在整体截图中的相对区域
qte_top_percent = 50
qte_bottom_percent = 97
qte_left_percent = 22
qte_right_percent = 100

; QTE 按键判定横向容差（参考分辨率像素），补偿高分辨率下光标在采样间隔内跨越色条
qte_press_tolerance_pixels = 0

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
yellow_lower_saturation = 125
yellow_lower_value = 220
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
white_upper_saturation = 10
white_upper_value = 255

; 挡板第一个颜色区间
blocker_one_lower_hue = 0
blocker_one_lower_saturation = 25
blocker_one_lower_value = 230
blocker_one_upper_hue = 180
blocker_one_upper_saturation = 52
blocker_one_upper_value = 255

; 挡板第二个颜色区间
blocker_two_lower_hue = 0
blocker_two_lower_saturation = 0
blocker_two_lower_value = 200
blocker_two_upper_hue = 180
blocker_two_upper_saturation = 10
blocker_two_upper_value = 245

; 参考分辨率下的挡板轮廓宽高限制（像素，判断时不包含上下限）
blocker_shape_min_width = 4
blocker_shape_max_width = 20
blocker_shape_min_height = 18
blocker_shape_max_height = 100

[backpack]
; 背包清理流程中，每次点击按钮前等待的秒数
button_click_interval_seconds = 2

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
quit_backpack_top = 0.05

[time]
; 一轮钓鱼结束后等待的时间，根据网络情况可以调整
round_end_wait_time = 4

; 钓鱼成功后的停留时间，来等待动画效果结束，根据电脑情况可以调整
fish_end_wait_time = 4

; 执行脚本后的停留时间，来预留时间能切换到游戏界面
begin_fish_wait_time = 4

; 热循环的轻量节流时间，减轻 CPU 占用
loop_sleep_seconds = 0.02

; 钓鱼的最长持续时间，用于防止错误一直退出不了qte时刻
longest_keep_time = 35

[scale]
; 像素阈值调试时使用的参考窗口尺寸
reference_window_width = 1152
reference_window_height = 648

[ocr]
; 程序启动时是否执行一次 OCR 目标区域调试
enabled = true
debug_once_on_start = true
auto_select_strategy = true

; OCR 未识别到“时”时是否自动切换钓点
change_location_on_missing_time = false

location_left_percent = 11
location_top_percent = 8
location_right_percent = 28
location_bottom_percent = 15
backpack_full_left_percent = 30
backpack_full_top_percent = 20
backpack_full_right_percent = 65
backpack_full_bottom_percent = 30
use_cls = false
; 模型路径留空时使用 RapidOCR 包内置模型
det_model_path =
cls_model_path =
rec_model_path =
rec_keys_path =
"""
