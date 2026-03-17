from __future__ import annotations

from enum import Enum
import threading
import time

import cv2
import numpy as np

from actions import ActionExecutor
from capture import WindowCaptureBuffer
from detectors import HookDetector
from qte_strategy import BaseQTEStrategy
import utils

import random


class FishingState(Enum):
    CAST = "CAST"
    WAITING_BITE = "WAITING_BITE"
    QTE = "QTE"
    ROUND_END = "ROUND_END"
   
hookWindowTitle = {
    "ORIG" : "HOOK_ORIG",
    "MASK" : "Hook Mask"
}

# 核心引擎：单线程状态机，负责读取帧、判断、调度动作
class AutoFishingEngine:
    def __init__(
        self,
        config,
        hwnd,
        capture: WindowCaptureBuffer,
        actions: ActionExecutor,
        strategy: BaseQTEStrategy,
        debug: bool = False,
        debug_show_windows: bool = True,
        debug_show_windows_config: tuple[bool, bool] = (True, True),
        stats_interval: float = 1.0,
    ) -> None:
        self._config = config
        self.hwnd = hwnd
        self._capture = capture
        self._actions = actions
        self._strategy = strategy
        self._debug = debug
        self._debug_show_windows = debug_show_windows
        self._debug_show_hook_windows, self._debug_show_qte_windows = debug_show_windows_config
        self._stats_interval = max(stats_interval, 0.2)
        self._last_stats_at = time.monotonic()
        self._last_stats_frame_id = 0
        self._processed_frames = 0
        self._debug_windows: set[str] = set()

        self._hook_detector = HookDetector(
            lower_yellow=np.array(
                [
                    utils.read_config_int(config, "hook", "hook_lower_yellow_hue"),
                    utils.read_config_int(config, "hook", "hook_lower_yellow_saturation"),
                    utils.read_config_int(config, "hook", "hook_lower_yellow_value"),
                ]
            ),
            upper_yellow=np.array(
                [
                    utils.read_config_int(config, "hook", "hook_upper_yellow_hue"),
                    utils.read_config_int(config, "hook", "hook_upper_yellow_saturation"),
                    utils.read_config_int(config, "hook", "hook_upper_yellow_value"),
                ]
            ),
            top_percent=utils.read_config_int(config, "hook", "top_percent"),
            bottom_percent=utils.read_config_int(config, "hook", "bottom_percent"),
            left_percent=utils.read_config_int(config, "hook", "left_percent"),
            right_percent=utils.read_config_int(config, "hook", "right_percent"),
            hwnd=hwnd,
        )

        # 抛杆操作的位置
        self._hold_mouse_x_percent = utils.read_config_int(config, "hook", "hold_mouse_x_percent")
        self._hold_mouse_y_percent = utils.read_config_int(config, "hook", "hold_mouse_y_percent")
        # 抛竿动作持续时间
        self._cast_hold_seconds = 0.45
        # 抛竿后到可以检测上钩的等待时间
        self._cast_recover_seconds = 1.0
        # 收杆后进入 QTE 的等待时间
        self._bite_to_qte_seconds = 0.6
        self._fish_end_wait_seconds = float(config["time"]["fish_end_wait_time"])
        self._round_end_wait_seconds = float(config["time"]["round_end_wait_time"])
        # 等待上钩超时后重新抛杆
        self._wait_timeout_seconds = utils.read_config_float(config, "time", "wait_bite_timeout", 12)
        self._waiting_started_at = time.monotonic()

        self._state = FishingState.CAST
        self._state_started_at = time.monotonic()
        # 非阻塞延时：在 blocked_until 前不做处理
        self._blocked_until = self._state_started_at + float(
            config["time"]["begin_fish_wait_time"]
        )

        self._last_frame_id = 0
        self._stop_requested = threading.Event()
        self._thread = threading.Thread(
            target=self._run,
            name="fishing-engine",
            daemon=True,
        )
        
        # self._setup_debug_window(hookWindowTitle["ORIG"], (0, 0))

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop_requested.set()
        self._thread.join(timeout=1)

    def _run(self) -> None:
        # 主循环只处理“最新帧”，不阻塞采集回调
        while not self._stop_requested.is_set() and not self._capture.closed.is_set():
            frame, frame_id, updated_at = self._capture.get_latest()
            # 没有新帧，或帧 ID 没有更新，说明还在等新帧到来，短暂休眠避免空转
            if frame is None or frame_id == self._last_frame_id:
                time.sleep(0.005)
                continue

            self._last_frame_id = frame_id
            now = time.monotonic()
            self._processed_frames += 1
            # 调试模式下定期输出状态和性能统计信息，帮助调整参数和排查问题
            if self._debug:
                self._maybe_log_stats(now, frame_id, updated_at)
            if now < self._blocked_until:
                continue

            if self._state == FishingState.CAST:
                self._handle_cast()
                continue

            if self._state == FishingState.WAITING_BITE:
                self._handle_waiting_bite(frame)
                continue

            if self._state == FishingState.QTE:
                self._handle_qte(frame)
                continue
            
            if self._state == FishingState.ROUND_END:
                self._handle_round_end()
                continue


    def _set_state(self, state: FishingState, delay: float = 0.0) -> None:
        # 统一状态切换入口
        previous_state = self._state
        self._state = state
        self._state_started_at = time.monotonic()
        self._blocked_until = self._state_started_at + max(delay, 0.0)

        if state == FishingState.QTE:
            self._strategy.reset()
        if state == FishingState.WAITING_BITE or state == FishingState.ROUND_END:
            self._waiting_started_at = time.monotonic()

        print(
            f">>> [STATE] {previous_state.value} -> {state.value}, "
            f"blocked for {delay:.2f}s"
        )

    def _handle_cast(self) -> None:
        print(">>> Casting...")        
        # utils.relative_point()
        self._actions.hold("space", duration=self._cast_hold_seconds)
        # 传入你的游戏窗口句柄、坐标和长按时间
        
        self._set_state(FishingState.WAITING_BITE, delay=self._cast_recover_seconds)

    def _handle_waiting_bite(self, frame) -> None:
        if self._debug and self._debug_show_windows and self._debug_show_hook_windows:
            roi_bgr, mask, _pixel_count = self._hook_detector.debug_view(frame)
            self._update_debug_windows(
                [
                    (hookWindowTitle["ORIG"], roi_bgr),
                    (hookWindowTitle["MASK"], mask),
                ]
            )

        now = time.monotonic()
        if now - self._waiting_started_at > self._wait_timeout_seconds:
            print(">>> Waiting bite timeout, recasting.")
            self._set_state(FishingState.CAST, delay=1)
            return

        detection = self._hook_detector.detect(frame)
        if not detection.matched:
            return

        print(f">>> Fish hooked, yellow pixels={detection.pixel_count}")
        self._actions.press("space")
        self._set_state(FishingState.QTE, delay=self._bite_to_qte_seconds)

    def _handle_qte(self, frame) -> None:
        # QTE 策略只返回“是否按键/是否结束”
        # if self._debug and self._debug_show_windows and self._debug_show_qte_windows:
        #     self._update_debug_windows(self._strategy.debug_view(frame))

        # result = self._strategy.step(frame)
        # if result.press_space:
        #     self._actions.press("space")

        # if not result.finished:
        #     return

        # print(">>> QTE finished")
        # region = utils.get_client_region(self.hwnd)
        # if not region:
        #     print(">>> Window region not found, skip click.")
        # else:
        #     center = utils.window_center(region)
        #     self._actions.click(
        #         center[0],
        #         center[1],
        #         delay=self._fish_end_wait_seconds,
        #     )
        # total_delay = self._fish_end_wait_seconds + self._round_end_wait_seconds
        # self._set_state(FishingState.ROUND_END, delay=total_delay)
        
        
        # self._actions.press("space", 2)
        if self._debug and self._debug_show_windows and self._debug_show_qte_windows:
            self._update_debug_windows(self._strategy.debug_view(frame))

        result = self._strategy.step(frame)
        if result.press_space:
            self._actions.press("space")

        if not result.finished:
            return
        
        print(">>> QTE finished, waiting for fish animation...")

        # QTE 刚刚结束，只等待拉鱼动画的时间
        self._set_state(FishingState.ROUND_END, delay=self._fish_end_wait_seconds)

    def _handle_round_end(self) -> None:
        # print(">>> Closing settlement UI...")
        
        # 1. 此时拉鱼动画已结束，UI 应该出现了，我们发送按键关闭它
        # 很多游戏用空格/ESC关闭 UI 比鼠标点击中心点更稳，你可以根据游戏实际情况选择
        # self._actions.press("space") 
        # 如果必须点击，可以这样写：
        region = utils.get_client_region(self.hwnd)
        center = utils.window_center(region)
        self._actions.click(center[0], center[1])

        print(">>> UI closed, waiting before next cast.")
        # self._actions.clear_pending_actions()
        # 2. 关闭 UI 后，稍微休息一下，确保人物回到空闲状态，再进入抛竿阶段
        self._set_state(FishingState.CAST, delay=self._round_end_wait_seconds)


    def _maybe_log_stats(self, now: float, frame_id: int, updated_at: float) -> None:
        if now - self._last_stats_at < self._stats_interval:
            return

        elapsed = now - self._last_stats_at
        capture_fps = (frame_id - self._last_stats_frame_id) / elapsed if elapsed > 0 else 0.0
        engine_fps = self._processed_frames / elapsed if elapsed > 0 else 0.0
        queue_len = self._actions.get_queue_size()
        frame_age_ms = (now - updated_at) * 1000 if updated_at > 0 else -1

        print(
            ">>> [状态信息] "
            f"state={self._state.value} "
            f"capture_fps={capture_fps:.1f} "
            f"engine_fps={engine_fps:.1f} "
            f"queue={queue_len} "
            f"frame_age_ms={frame_age_ms:.1f}"
        )

        self._last_stats_at = now
        self._last_stats_frame_id = frame_id
        self._processed_frames = 0

    def _update_debug_windows(self, images: list[tuple[str, np.ndarray]]) -> None:
        for name, image in images:
            cv2.imshow(name, image)
        cv2.waitKey(1)
        
    def _setup_debug_window(self, name: str, position: tuple[int, int]) -> None:
        if name not in self._debug_windows:
            cv2.namedWindow(name, cv2.WINDOW_NORMAL)
            cv2.moveWindow(name, position[0], position[1])
            self._debug_windows.add(name)
