from __future__ import annotations

import configparser
import time

import cv2
import numpy as np
import pydirectinput

import utils
from utils import Rect

DEFAULT_LOOP_SLEEP_SECONDS = 0.005


class BaseQTEStrategy:
    def __init__(self, config: configparser.ConfigParser, region: Rect) -> None:
        self.region = region
        self.pixel_threshold_scale = utils.build_pixel_threshold_scale(config, region)
        self.longest_keep_time = utils.read_config_int(config, "time", "longest_keep_time")
        self.fish_end_wait_time = utils.read_config_float(config, "time", "fish_end_wait_time")
        self.loop_sleep_seconds = config.getfloat(
            "time",
            "loop_sleep_seconds",
            fallback=DEFAULT_LOOP_SLEEP_SECONDS,
        )
        self.time_bar_score_threshold = utils.scale_pixel_threshold(
            50,
            self.pixel_threshold_scale,
        )
        self.ice_trouble_pixel_threshold = utils.scale_pixel_threshold(
            5,
            self.pixel_threshold_scale,
        )
        self.abyss_yellow_pixel_threshold = utils.scale_pixel_threshold(
            300,
            self.pixel_threshold_scale,
        )

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
        self.time_pos = (
            config.getint("roi", "time_top_percent"),
            config.getint("roi", "time_bottom_percent"),
            config.getint("roi", "time_left_percent"),
            config.getint("roi", "time_right_percent")
        )
        self.qte_pos = (
            config.getint("roi", "qte_top_percent"),
            config.getint("roi", "qte_bottom_percent"),
            config.getint("roi", "qte_left_percent"),
            config.getint("roi", "qte_right_percent"),
        )
        print(
            ">>> QTE 像素阈值: "
            f"time_bar_score={self.time_bar_score_threshold}, "
            f"ice_trouble={self.ice_trouble_pixel_threshold}, "
            f"abyss_yellow={self.abyss_yellow_pixel_threshold}"
        )

    def play_qte(self, sct: utils.DxCameraCapture) -> None:
        raise NotImplementedError("子类必须实现 play_qte() 方法")

    def _sleep_loop(self) -> None:
        time.sleep(self.loop_sleep_seconds)

    def _grab_qte_frames(self, sct: utils.DxCameraCapture) -> np.ndarray | None:
        frame = sct.grab(self.roi_pos)
        if frame is None:
            return None
        frame_hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        return frame_hsv
    
    def _split_roi_and_time(self, frame_hsv: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        h, w = frame_hsv.shape[:2]
        roi_hsv = frame_hsv[
            h * self.time_pos[0] // 100 : h * self.time_pos[1] // 100,
            w * self.time_pos[2] // 100 : w * self.time_pos[3] // 100,
        ]
        time_hsv = frame_hsv[
            h * self.qte_pos[0] // 100 : h * self.qte_pos[1] // 100,
            w * self.qte_pos[2] // 100 : w * self.qte_pos[3] // 100,
        ]
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
        score = cv2.countNonZero(mask_red) + cv2.countNonZero(mask_green)
        return score > self.time_bar_score_threshold

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
        if no_bar_frames > 50:
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
        start_time = time.monotonic()

        while time.monotonic() - start_time < self.longest_keep_time:
            frames = self._grab_qte_frames(sct)
            if frames is None:
                self._sleep_loop()
                continue
            
            time_hsv, qte_hsv = self._split_roi_and_time(frames)
            if not self._time_bar_visible(time_hsv):
                no_bar_frames += 1
                if self._on_bar_disappeared(no_bar_frames):
                    break
                self._sleep_loop()
                continue

            no_bar_frames = 0
            
            if self.solve_ice_trouble(qte_hsv):
                print(">>> 破冰成功，继续钓鱼")
                self._sleep_loop()
                continue

            cursor_x = self._find_cursor_x(qte_hsv)
            if cursor_x is None:
                self._sleep_loop()
                continue

            mask_yellow = self._yellow_mask(qte_hsv)
            
            check_y = mask_yellow.shape[0] // 2
            if mask_yellow[check_y, cursor_x]:
                pydirectinput.press("space")
                pass
            self._sleep_loop()

    def solve_ice_trouble(self, roi_hsv: np.ndarray) -> bool:
        mask = cv2.inRange(roi_hsv, self.red_range.lower, self.red_range.upper)
        if cv2.countNonZero(mask) > self.ice_trouble_pixel_threshold:
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
        start_time = time.monotonic()

        while time.monotonic() - start_time < self.longest_keep_time:
            frames = self._grab_qte_frames(sct)
            if frames is None:
                self._sleep_loop()
                continue

            roi_hsv, time_hsv = frames
            if not self._time_bar_visible(time_hsv):
                no_bar_frames += 1
                if self._on_bar_disappeared(no_bar_frames):
                    break
                self._sleep_loop()
                continue

            no_bar_frames = 0
            cursor_x = self._find_cursor_x(roi_hsv)
            if cursor_x is None:
                self._sleep_loop()
                continue

            yellow_mask = self._yellow_mask(roi_hsv)
            blue_mask = utils.create_color_mask(self.blue_range.lower, self.blue_range.upper, roi_hsv)
            check_y = yellow_mask.shape[0] // 2

            if cv2.countNonZero(yellow_mask) > self.abyss_yellow_pixel_threshold:
                if yellow_mask[check_y, cursor_x]:
                    pydirectinput.press("space")
            elif blue_mask[check_y, cursor_x]:
                pydirectinput.press("space")
            self._sleep_loop()
