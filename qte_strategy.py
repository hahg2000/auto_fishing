from __future__ import annotations

from dataclasses import dataclass
import time

import cv2
import numpy as np

import utils


@dataclass
class QTEStepResult:
    # 策略只返回“是否按键/是否结束”，不直接执行输入
    press_space: bool = False
    finished: bool = False


class BaseQTEStrategy:
    def __init__(self, config, hwnd) -> None:
        self.hwnd = hwnd
        self.longest_keep_time = utils.read_config_int(config, "time", "longest_keep_time")

        self._lower_white = np.array(
            [
                utils.read_config_int(config, "roi", "lower_white_hue"),
                utils.read_config_int(config, "roi", "lower_white_saturation"),
                utils.read_config_int(config, "roi", "lower_white_value"),
            ]
        )
        self._upper_white = np.array(
            [
                utils.read_config_int(config, "roi", "upper_white_hue"),
                utils.read_config_int(config, "roi", "upper_white_saturation"),
                utils.read_config_int(config, "roi", "upper_white_value"),
            ]
        )
        self._lower_yellow = np.array(
            [
                utils.read_config_int(config, "roi", "lower_yellow_hue"),
                utils.read_config_int(config, "roi", "lower_yellow_saturation"),
                utils.read_config_int(config, "roi", "lower_yellow_value"),
            ]
        )
        self._upper_yellow = np.array(
            [
                utils.read_config_int(config, "roi", "upper_yellow_hue"),
                utils.read_config_int(config, "roi", "upper_yellow_saturation"),
                utils.read_config_int(config, "roi", "upper_yellow_value"),
            ]
        )
        self._time_lower_green = np.array(
            [
                utils.read_config_int(config, "roi", "time_lower_green_hue"),
                utils.read_config_int(config, "roi", "time_lower_green_saturation"),
                utils.read_config_int(config, "roi", "time_lower_green_value"),
            ]
        )
        self._time_upper_green = np.array(
            [
                utils.read_config_int(config, "roi", "time_upper_green_hue"),
                utils.read_config_int(config, "roi", "time_upper_green_saturation"),
                utils.read_config_int(config, "roi", "time_upper_green_value"),
            ]
        )
        self._time_lower_red = np.array(
            [
                utils.read_config_int(config, "roi", "time_lower_red_hue"),
                utils.read_config_int(config, "roi", "time_lower_red_saturation"),
                utils.read_config_int(config, "roi", "time_lower_red_value"),
            ]
        )
        self._time_upper_red = np.array(
            [
                utils.read_config_int(config, "roi", "time_upper_red_hue"),
                utils.read_config_int(config, "roi", "time_upper_red_saturation"),
                utils.read_config_int(config, "roi", "time_upper_red_value"),
            ]
        )

        self._qte_box = [
            utils.read_config_int(config, "roi", "top_percent"),
            utils.read_config_int(config, "roi", "bottom_percent"),
            utils.read_config_int(config, "roi", "left_percent"),
            utils.read_config_int(config, "roi", "right_percent"),
        ]
        self._time_box = [
            utils.read_config_int(config, "roi", "time_top_percent"),
            utils.read_config_int(config, "roi", "time_bottom_percent"),
            utils.read_config_int(config, "roi", "time_left_percent"),
            utils.read_config_int(config, "roi", "time_right_percent"),
        ]

        # 防止高帧率下重复触发按键
        # self._press_cooldown_seconds = 0.06
        self._press_cooldown_seconds = 0.1
        self.reset()

    def reset(self) -> None:
        # 每次进入 QTE 前重置状态
        self._no_bar_start_time = 0.0  # 抛弃帧数，改用时间戳
        self._last_press_at = 0.0
        self._started_at = time.monotonic()

    def step(self, frame: np.ndarray) -> QTEStepResult:
        # 单帧判断，不允许 sleep 或长循环
        raise NotImplementedError

    def _get_qte_hsv(self, pure_frame: np.ndarray) -> np.ndarray:
        return utils.to_hsv(utils.crop_frame(pure_frame, self._qte_box))

    def _get_time_hsv(self, pure_frame: np.ndarray) -> np.ndarray:
        return utils.to_hsv(utils.crop_frame(pure_frame, self._time_box))

    def _is_bar_active(self, time_hsv: np.ndarray) -> bool:
        mask_green = utils.create_color_mask(
            self._time_lower_green,
            self._time_upper_green,
            time_hsv,
            is_dilate=False,
        )
        mask_red = utils.create_color_mask(
            self._time_lower_red,
            self._time_upper_red,
            time_hsv,
            is_dilate=False,
        )
        red_pixels = cv2.countNonZero(mask_red) * 20
        green_pixels = cv2.countNonZero(mask_green) * 10
        return red_pixels + green_pixels > 1000

    def _get_cursor_x(self, qte_hsv: np.ndarray) -> int | None:
        mask_cursor = utils.create_color_mask(
            self._lower_white,
            self._upper_white,
            qte_hsv,
            is_dilate=False,
        )
        col_sums = np.sum(mask_cursor, axis=0)
        if np.max(col_sums) <= 0:
            return None
        return int(np.argmax(col_sums))

    def _consume_press_slot(self) -> bool:
        # 用冷却时间限制按键频率
        now = time.monotonic()
        if now - self._last_press_at < self._press_cooldown_seconds:
            print(">>> Press cooldown, skip")
            return False
        self._last_press_at = now
        return True

    def _track_no_bar(self, duration_seconds: float) -> QTEStepResult:
        now = time.monotonic()
        # 如果是第一次发现没有进度条，记录当前时间
        if self._no_bar_start_time == 0.0:
            self._no_bar_start_time = now

        # 如果消失的时间还没达到要求的阈值，继续保持 QTE 状态
        if now - self._no_bar_start_time <= duration_seconds:
            return QTEStepResult()

        self.reset()
        return QTEStepResult(finished=True)

    def debug_view(self, frame: np.ndarray) -> list[tuple[str, np.ndarray]]:
        # 返回调试窗口需要展示的图像
        qte_bgr = utils.to_bgr(utils.crop_frame(frame, self._qte_box))
        time_bgr = utils.to_bgr(utils.crop_frame(frame, self._time_box))
        qte_hsv = cv2.cvtColor(qte_bgr, cv2.COLOR_BGR2HSV)
        time_hsv = cv2.cvtColor(time_bgr, cv2.COLOR_BGR2HSV)

        mask_yellow = utils.create_color_mask(self._lower_yellow, self._upper_yellow, qte_hsv)
        mask_cursor = utils.create_color_mask(self._lower_white, self._upper_white, qte_hsv, is_dilate=False)
        mask_green = utils.create_color_mask(self._time_lower_green, self._time_upper_green, time_hsv, is_dilate=False)
        mask_red = utils.create_color_mask(self._time_lower_red, self._time_upper_red, time_hsv, is_dilate=False)

        return [
            ("QTE ROI", qte_bgr),
            ("QTE Yellow", mask_yellow),
            # ("QTE Cursor", mask_cursor),
            # ("Time ROI", time_bgr),
            # ("Time Green", mask_green),
            # ("Time Red", mask_red),
        ]


class FrostStraitQTEStrategy(BaseQTEStrategy):
    def __init__(self, config, hwnd) -> None:
        super().__init__(config, hwnd)
        self._lower_red = np.array(
            [
                utils.read_config_int(config, "roi", "lower_red_hue"),
                utils.read_config_int(config, "roi", "lower_red_saturation"),
                utils.read_config_int(config, "roi", "lower_red_value"),
            ]
        )
        self._upper_red = np.array(
            [
                utils.read_config_int(config, "roi", "upper_red_hue"),
                utils.read_config_int(config, "roi", "upper_red_saturation"),
                utils.read_config_int(config, "roi", "upper_red_value"),
            ]
        )

    def step(self, frame: np.ndarray) -> QTEStepResult:
        if time.monotonic() - self._started_at > self.longest_keep_time:
            self.reset()
            return QTEStepResult(finished=True)

        pure_frame = utils.get_pure_game_frame(self.hwnd, frame)
        qte_hsv = self._get_qte_hsv(pure_frame)
        time_hsv = self._get_time_hsv(pure_frame)
        if not self._is_bar_active(time_hsv):
            return self._track_no_bar(duration_seconds=1.0)

        self._no_bar_start_time = 0.0  # 重置无进度条计时
        if self._detect_ice(qte_hsv) and self._consume_press_slot():
            return QTEStepResult(press_space=True)

        cursor_x = self._get_cursor_x(qte_hsv)
        if cursor_x is None:
            return QTEStepResult()

        mask_yellow = utils.create_color_mask(self._lower_yellow, self._upper_yellow, qte_hsv)
        check_y = qte_hsv.shape[0] // 2
        if mask_yellow[check_y, cursor_x] and self._consume_press_slot():
            return QTEStepResult(press_space=True)

        return QTEStepResult()

    def _detect_ice(self, qte_hsv: np.ndarray) -> bool:
        ice_mask = cv2.inRange(qte_hsv, self._lower_red, self._upper_red)
        return cv2.countNonZero(ice_mask) > 5

    def debug_view(self, frame: np.ndarray) -> list[tuple[str, np.ndarray]]:
        views = super().debug_view(frame)
        pure_frame = utils.get_pure_game_frame(self.hwnd, frame)
        qte_hsv = self._get_qte_hsv(pure_frame)
        ice_mask = cv2.inRange(qte_hsv, self._lower_red, self._upper_red)
        views.append(("QTE Ice", ice_mask))
        return views


class AbyssMawQTEStrategy(BaseQTEStrategy):
    def __init__(self, config, hwnd) -> None:
        super().__init__(config, hwnd)
        self._lower_blue = np.array(
            [
                utils.read_config_int(config, "roi", "lower_blue_hue"),
                utils.read_config_int(config, "roi", "lower_blue_saturation"),
                utils.read_config_int(config, "roi", "lower_blue_value"),
            ]
        )
        self._upper_blue = np.array(
            [
                utils.read_config_int(config, "roi", "upper_blue_hue"),
                utils.read_config_int(config, "roi", "upper_blue_saturation"),
                utils.read_config_int(config, "roi", "upper_blue_value"),
            ]
        )

    def step(self, frame: np.ndarray) -> QTEStepResult:
        if time.monotonic() - self._started_at > self.longest_keep_time:
            self.reset()
            return QTEStepResult(finished=True)

        pure_frame = utils.get_pure_game_frame(self.hwnd, frame)
        qte_hsv = self._get_qte_hsv(pure_frame)
        time_hsv = self._get_time_hsv(pure_frame)
        if not self._is_bar_active(time_hsv):
            return self._track_no_bar(1)

        self._no_bar_frames = 0
        cursor_x = self._get_cursor_x(qte_hsv)
        if cursor_x is None:
            return QTEStepResult()

        mask_yellow = utils.create_color_mask(self._lower_yellow, self._upper_yellow, qte_hsv)
        mask_blue = utils.create_color_mask(self._lower_blue, self._upper_blue, qte_hsv)
        check_y = qte_hsv.shape[0] // 2

        if cv2.countNonZero(mask_yellow) > 300:
            target_mask = mask_yellow
        else:
            target_mask = mask_blue

        if target_mask[check_y, cursor_x] and self._consume_press_slot():
            return QTEStepResult(press_space=True)

        return QTEStepResult()

    def debug_view(self, frame: np.ndarray) -> list[tuple[str, np.ndarray]]:
        views = super().debug_view(frame)
        pure_frame = utils.get_pure_game_frame(self.hwnd, frame)
        qte_hsv = self._get_qte_hsv(pure_frame)
        mask_blue = utils.create_color_mask(self._lower_blue, self._upper_blue, qte_hsv)
        views.append(("QTE Blue", mask_blue))
        return views
