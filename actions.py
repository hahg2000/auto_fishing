from __future__ import annotations

from dataclasses import dataclass, field
import heapq
import threading
import time

import pydirectinput


pydirectinput.PAUSE = 0

# ordereable 的 dataclass 用于动作队列，按 execute_at 和 sequence 排序
@dataclass(order=True)
class ScheduledAction:
    execute_at: float
    sequence: int
    # compare=False 表示不参与排序，kind 和 payload 只在执行时使用
    kind: str = field(compare=False)
    # 执行动作所需的参数，例如按键名、坐标等
    payload: tuple = field(compare=False)


# 动作执行器：单独线程串行执行所有输入动作，避免多线程同时按键冲突
class ActionExecutor:
    def __init__(self) -> None:
        self._condition = threading.Condition()
        self._queue: list[ScheduledAction] = []
        self._sequence = 0
        self._stop_requested = False
        self._thread = threading.Thread(
            target=self._run,
            name="action-executor",
            daemon=True,
        )

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        with self._condition:
            self._stop_requested = True
            # 清空队列，避免退出后仍执行延迟动作
            self._queue.clear()
            self._condition.notify_all()
        self._thread.join(timeout=1)
        
    def clear_pending_actions(self) -> None:
        with self._condition:
            # 清空队列，避免退出后仍执行延迟动作
            self._queue.clear()
            self._condition.notify_all()
        self._thread.join(timeout=1)

    def press(self, key: str, delay: float = 0.0) -> None:
        self._submit("press", (key,), delay)

    def hold(self, key: str, duration: float, delay: float = 0.0) -> None:
        self._submit("hold", (key, duration), delay)

    def click(self, x: int, y: int, delay: float = 0.0) -> None:
        self._submit("click", (x, y), delay)

    def get_queue_size(self) -> int:
        # 供统计使用：当前队列中待执行的动作数量
        with self._condition:
            return len(self._queue)

    def _submit(self, kind: str, payload: tuple, delay: float) -> None:
        with self._condition:
            # 使用单调时钟计算执行时间，避免系统时间调整带来的偏差
            action = ScheduledAction(
                execute_at=time.monotonic() + max(delay, 0.0),
                sequence=self._sequence,
                kind=kind,
                payload=payload,
            )
            self._sequence += 1
            # 使用堆结构保持队列按 execute_at 自动排序，确保动作按时间执行
            heapq.heappush(self._queue, action)
            self._condition.notify()

    def _run(self) -> None:
        # 消费线程：按时间顺序执行动作
        while True:
            with self._condition:
                while True:
                    # 优先检查停止标志，确保及时退出
                    if self._stop_requested and not self._queue:
                        return
                    # 队列为空，等待新动作
                    if not self._queue:
                        self._condition.wait()
                        continue

                    wait_time = self._queue[0].execute_at - time.monotonic()
                    if wait_time > 0:
                        # 还没到时间，等待
                        self._condition.wait(timeout=wait_time)
                        continue

                    # 时间到了，取出动作执行
                    action = heapq.heappop(self._queue)
                    break
            print(f"执行了{action}")
            self._execute(action)

    def _execute(self, action: ScheduledAction) -> None:
        if action.kind == "press":
            (key,) = action.payload
            pydirectinput.press(key)
            return

        if action.kind == "hold":
            print(f"按住{action.payload}")
            key, duration = action.payload
            pydirectinput.keyDown(key)
            time.sleep(duration)
            pydirectinput.keyUp(key)
            return

        if action.kind == "click":
            x, y = action.payload
            pydirectinput.click(x, y)
            return

        raise ValueError(f"未知的动作类型: {action.kind}")
