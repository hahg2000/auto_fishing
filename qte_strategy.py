from __future__ import annotations

import configparser
import time

import cv2
import numpy as np
import pydirectinput

import utils
from utils import Rect


class BaseQTEStrategy:
    def __init__(self, config: configparser.ConfigParser, region: Rect) -> None:
        self.region = region
        self.longest_keep_time = utils.read_config_int(config, "time", "longest_keep_time")
        self.fish_end_wait_time = utils.read_config_float(config, "time", "fish_end_wait_time")

        self.white_range = utils.read_hsv_range(config, "roi", "white")
        self.yellow_range = utils.read_hsv_range(config, "roi", "yellow")
        self.time_green_range = utils.read_hsv_range_from_keys(
            config,
            "roi",
            lower_prefix="time_lower_green",
            upper_prefix="time_upper_green",
        )
        self.time_red_range = utils.read_hsv_range_from_keys(
            config,
            "roi",
            lower_prefix="time_lower_red",
            upper_prefix="time_upper_red",
        )
        self.roi_pos = utils.build_region_from_config(config, "roi", region)
        self.time_pos = utils.build_region_from_config(config, "roi", region, prefix="time")

    def play_qte(self, sct: utils.DxCameraCapture) -> None:
        raise NotImplementedError("子类必须实现 play_qte() 方法")

    def _grab_hsv_frame(self, sct: utils.DxCameraCapture, region: Rect) -> np.ndarray | None:
        frame = sct.grab(region)
        if frame is None:
            return None
        return cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

    def _grab_qte_frames(self, sct: utils.DxCameraCapture) -> tuple[np.ndarray, np.ndarray] | None:
        roi_hsv = self._grab_hsv_frame(sct, self.roi_pos)
        time_hsv = self._grab_hsv_frame(sct, self.time_pos)
        if roi_hsv is None or time_hsv is None:
            return None
        return roi_hsv, time_hsv

    def _time_bar_visible(self, time_hsv: np.ndarray) -> bool:
        mask_green = utils.create_color_mask(
            self.time_green_range.lower,
            self.time_green_range.upper,
            time_hsv,
            is_dilate=False,
        )
        mask_red = utils.create_color_mask(
            self.time_red_range.lower,
            self.time_red_range.upper,
            time_hsv,
            is_dilate=False,
        )
        score = cv2.countNonZero(mask_red) * 20 + cv2.countNonZero(mask_green) * 10
        return score > 1000

    def _find_cursor_x(self, roi_hsv: np.ndarray) -> int | None:
        mask_cursor = utils.create_color_mask(
            self.white_range.lower,
            self.white_range.upper,
            roi_hsv,
            is_dilate=False,
        )
        col_sums = np.sum(mask_cursor, axis=0)
        if np.max(col_sums) <= 0:
            return None
        return int(np.argmax(col_sums))

    def _finish_fishing(self) -> None:
        time.sleep(self.fish_end_wait_time)
        window_center_x, window_center_y = self.region.center
        pydirectinput.moveTo(window_center_x, window_center_y)
        time.sleep(0.2)
        pydirectinput.click()

    def _yellow_mask(self, roi_hsv: np.ndarray) -> np.ndarray:
        return utils.create_color_mask(self.yellow_range.lower, self.yellow_range.upper, roi_hsv)

    def _on_bar_disappeared(self, no_bar_frames: int) -> bool:
        if no_bar_frames > 30:
            print(">>> 钓鱼结束")
            self._finish_fishing()
            return True
        return False


class FrostStraitQTEStrategy(BaseQTEStrategy):
    """默认钓鱼点：只看黄色条，并处理破冰。"""

    def __init__(self, config: configparser.ConfigParser, region: Rect) -> None:
        super().__init__(config, region)
        self.red_range = utils.read_hsv_range(config, "roi", "red")

    def play_qte(self, sct: utils.DxCameraCapture) -> None:
        print(">>> 开始 QTE...")
        no_bar_frames = 0
        start_time = time.time()

        while time.time() - start_time < self.longest_keep_time:
            frames = self._grab_qte_frames(sct)
            if frames is None:
                continue

            roi_hsv, time_hsv = frames
            if not self._time_bar_visible(time_hsv):
                no_bar_frames += 1
                if self._on_bar_disappeared(no_bar_frames):
                    break
                continue

            no_bar_frames = 0
            if self.solve_ice_trouble(roi_hsv):
                continue

            cursor_x = self._find_cursor_x(roi_hsv)
            if cursor_x is None:
                continue

            mask_yellow = self._yellow_mask(roi_hsv)
            check_y = mask_yellow.shape[0] // 2
            if mask_yellow[check_y, cursor_x]:
                print(">>> 击中了黄色区域")
                pydirectinput.press("space")

    def solve_ice_trouble(self, roi_hsv: np.ndarray) -> bool:
        mask = cv2.inRange(roi_hsv, self.red_range.lower, self.red_range.upper)
        if cv2.countNonZero(mask) > 5:
            print(">>> 检测到冰冻！正在破冰 (按空格)...")
            pydirectinput.press("space")
            time.sleep(0.05)
            return True
        return False


class AbyssMawQTEStrategy(BaseQTEStrategy):
    def __init__(self, config: configparser.ConfigParser, region: Rect) -> None:
        super().__init__(config, region)
        self.blue_range = utils.read_hsv_range(config, "roi", "blue")

    def play_qte(self, sct: utils.DxCameraCapture) -> None:
        print(">>> 开始 QTE...")
        no_bar_frames = 0
        start_time = time.time()

        while time.time() - start_time < self.longest_keep_time:
            frames = self._grab_qte_frames(sct)
            if frames is None:
                continue

            roi_hsv, time_hsv = frames
            if not self._time_bar_visible(time_hsv):
                no_bar_frames += 1
                if self._on_bar_disappeared(no_bar_frames):
                    break
                continue

            no_bar_frames = 0
            cursor_x = self._find_cursor_x(roi_hsv)
            if cursor_x is None:
                continue

            yellow_mask = self._yellow_mask(roi_hsv)
            blue_mask = utils.create_color_mask(self.blue_range.lower, self.blue_range.upper, roi_hsv)
            check_y = yellow_mask.shape[0] // 2

            if cv2.countNonZero(yellow_mask) > 300:
                if yellow_mask[check_y, cursor_x]:
                    print(">>> 击中了黄色区域")
                    pydirectinput.press("space")
            elif blue_mask[check_y, cursor_x]:
                print(">>> 击中了蓝色区域")
                pydirectinput.press("space")
