from __future__ import annotations

import threading
import time
import win32gui
import numpy as np
import dxcam

class WindowCaptureBuffer:
    def __init__(self, window_name: str, target_fps: int = 60) -> None:
        self.closed = threading.Event()
        self._lock = threading.Lock()
        self._frame: np.ndarray | None = None
        self._frame_id = 0
        self._updated_at = 0.0
        
        self.window_name = window_name
        self.hwnd = win32gui.FindWindow(None, window_name)
        if not self.hwnd:
            raise ValueError(f"找不到游戏窗口: {window_name}")

        # dxcam 直接输出 BGR (3通道)，完美契合 OpenCV
        self._capture = dxcam.create(output_color="BGR")
        self.target_fps = target_fps

    def start(self) -> None:
        """
        开始抓取。
        原 WGC 的 start 是阻塞的，所以这里我们用一个 while 循环维持阻塞状态，
        顺便充当底层 Ring Buffer 到上层 _frame 状态的“搬运工”。
        """
        # 1. 计算游戏窗口真正的渲染区域（剔除标题栏和边框）
        # 这样 dxcam 抓出来的图尺寸和以前 WGC 抓的完全一致
        left, top, right, bottom = win32gui.GetClientRect(self.hwnd)
        left, top = win32gui.ClientToScreen(self.hwnd, (left, top))
        right, bottom = win32gui.ClientToScreen(self.hwnd, (right, bottom))
        region = (left, top, right, bottom)

        # 2. 启动 dxcam 后台异步抓取线程
        self._capture.start(target_fps=self.target_fps, region=region)
        print(f"DXCAM started. Target FPS: {self.target_fps}, Region: {region}")

        # 3. 阻塞当前线程，模拟 WGC 原来的阻塞行为，并模拟 on_frame_arrived 回调
        try:
            while not self.closed.is_set():
                # 检测游戏窗口是否被关闭
                if not win32gui.IsWindow(self.hwnd):
                    self.on_closed()
                    break

                # 从 dxcam 的 Ring Buffer 中拉取最新帧
                new_frame = self._capture.get_latest_frame()
                
                # 如果画面有更新 (new_frame 不为 None)
                if new_frame is not None:
                    with self._lock:
                        # dxcam 返回的本身就是 numpy array，且异步模式下已拷贝
                        self._frame = new_frame
                        self._frame_id += 1
                        self._updated_at = time.monotonic()

                # 短暂休眠，防止死循环跑满单核 CPU。休眠时间略少于帧生成间隔即可。
                time.sleep(1.0 / (self.target_fps * 2))
        finally:
            self._capture.stop()
            print("DXCAM stopped.")

    def get_latest(self) -> tuple[np.ndarray | None, int, float]:
        with self._lock:
            return self._frame, self._frame_id, self._updated_at

    def on_closed(self) -> None:
        self.closed.set()
        print("Game window closed.")