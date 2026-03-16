from __future__ import annotations

import threading
import time

import numpy as np
from windows_capture import Frame, InternalCaptureControl, WindowsCapture


# 采集层：只负责抓取最新一帧，不做业务逻辑
class WindowCaptureBuffer:
    def __init__(self, window_name: str) -> None:
        self.closed = threading.Event()
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._frame_id = 0
        self._updated_at = 0.0

        self._capture = WindowsCapture(
            cursor_capture=False,
            draw_border=False,
            window_name=window_name,
        )
        self._capture.event(self.on_frame_arrived) # type: ignore
        self._capture.event(self.on_closed) # type: ignore

    def start(self) -> None:
        # WindowsCapture 的 start 是阻塞式的
        self._capture.start()

    def get_latest(self) -> tuple[np.ndarray | None, int, float]:
        # 读取最新帧，配合 engine 的轮询
        with self._lock:
            return self._frame, self._frame_id, self._updated_at

    def on_frame_arrived(
        self,
        frame: Frame,
        capture_control: InternalCaptureControl,
    ) -> None:
        del capture_control
        # 回调线程里拷贝一份，避免底层缓冲区复用导致数据变化
        frame_buffer = np.asarray(frame.frame_buffer).copy()
        with self._lock:
            self._frame = frame_buffer
            self._frame_id += 1
            self._updated_at = time.monotonic()

    def on_closed(self) -> None:
        self.closed.set()
        print("Game window closed.")
