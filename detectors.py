from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np

import utils


@dataclass
class HookDetection:
    matched: bool
    pixel_count: int


# 鱼上钩检测：根据 HSV 颜色范围做像素计数
class HookDetector:
    def __init__(
        self,
        lower_yellow: np.ndarray,
        upper_yellow: np.ndarray,
        top_percent: int,
        bottom_percent: int,
        left_percent: int,
        right_percent: int,
        pixel_threshold: int = 250,
        pixel_scale_base: int = 648,
        hwnd=None,
    ) -> None:
        self._box = [
            top_percent,
            bottom_percent,
            left_percent,
            right_percent,
        ]
        self._lower_yellow = lower_yellow
        self._upper_yellow = upper_yellow
        self._pixel_threshold = pixel_threshold
        # 游戏的最小分辨率高度为648
        # self._pixel_scale_percent = pixel_scale_base / pixel_threshold
        self.hwnd = hwnd

    def scaled_pixel_threshold(self, pure_frame: np.ndarray) -> int:
        # 根据当前分辨率与基准分辨率的比例缩放像素计数
        return int((pure_frame.shape[0] / 648) ** 2 * self._pixel_threshold)   

    def detect(self, frame: np.ndarray) -> HookDetection:
        pure_frame = utils.get_pure_game_frame(self.hwnd, frame)
        hook_img = utils.crop_frame(pure_frame, self._box)
        hook_hsv = utils.to_hsv(hook_img)
        hook_yellow = utils.create_color_mask(
            self._lower_yellow,
            self._upper_yellow,
            hook_hsv,
            is_dilate=False,
        )
        pixel_count = int(cv2.countNonZero(hook_yellow))
        return HookDetection(pixel_count > self.scaled_pixel_threshold(pure_frame), pixel_count)

    def debug_view(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray, int]:
        pure_frame = utils.get_pure_game_frame(self.hwnd, frame)
        hook_img = utils.crop_frame(pure_frame, self._box)
        hook_bgr = utils.to_bgr(hook_img)
        hook_hsv = cv2.cvtColor(hook_img, cv2.COLOR_BGR2HSV)
        hook_yellow = utils.create_color_mask(
            self._lower_yellow,
            self._upper_yellow,
            hook_hsv,
            is_dilate=False,
        )
        
        pixel_count = int(cv2.countNonZero(hook_yellow))
        self.scaled_pixel = self.scaled_pixel_threshold(pure_frame)
        return hook_bgr, hook_yellow, pixel_count
