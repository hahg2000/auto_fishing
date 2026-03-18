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
        # 逻辑时间线：只约束“仍在队列中的动作”之间的先后顺序。
        # 这样 hold 拆分成 key_down/key_up 后，后续 delay=0 的动作仍会排在 key_up 之后，
        # 但不会被“已经执行完的历史动作”错误地拖到未来。
        self._timeline_at = 0.0
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
            self._timeline_at = time.monotonic()
            self._condition.notify_all()
        self._thread.join(timeout=1)
        
    def clear_pending_actions(self) -> None:
        with self._condition:
            # 清空队列，避免退出后仍执行延迟动作
            self._queue.clear()
            self._timeline_at = time.monotonic()
            self._condition.notify_all()

    def press(self, key: str, delay: float = 0.0) -> None:
        self._submit("press", (key,), delay)

    def hold(self, key: str, duration: float, delay: float = 0.0) -> None:
        self._submit_hold(key, duration, delay)

    def click(self, x: int, y: int, delay: float = 0.0) -> None:
        self._submit("click", (x, y), delay)

    def get_queue_size(self) -> int:
        # 供统计使用：当前队列中待执行的动作数量
        with self._condition:
            return len(self._queue)

    def _submit(self, kind: str, payload: tuple, delay: float) -> None:
        with self._condition:
            # 使用单调时钟计算执行时间，避免系统时间调整带来的偏差
            now = time.monotonic()
            execute_at = max(now + max(delay, 0.0), self._timeline_at)
            action = ScheduledAction(
                execute_at=execute_at,
                sequence=self._sequence,
                kind=kind,
                payload=payload,
            )
            self._sequence += 1
            self._timeline_at = execute_at
            # 使用堆结构保持队列按 execute_at 自动排序，确保动作按时间执行
            heapq.heappush(self._queue, action)
            self._condition.notify()

    def _submit_hold(self, key: str, duration: float, delay: float) -> None:
        hold_seconds = max(duration, 0.0)
        with self._condition:
            now = time.monotonic()
            press_at = max(now + max(delay, 0.0), self._timeline_at)
            release_at = press_at + hold_seconds

            keydown_action = ScheduledAction(
                execute_at=press_at,
                sequence=self._sequence,
                kind="key_down",
                payload=(key,),
            )
            self._sequence += 1

            keyup_action = ScheduledAction(
                execute_at=release_at,
                sequence=self._sequence,
                kind="key_up",
                payload=(key,),
            )
            self._sequence += 1

            self._timeline_at = release_at
            heapq.heappush(self._queue, keydown_action)
            heapq.heappush(self._queue, keyup_action)
            self._condition.notify_all()

    def _refresh_timeline_locked(self) -> None:
        if not self._queue:
            self._timeline_at = time.monotonic()
            return
        self._timeline_at = max(action.execute_at for action in self._queue)

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
                    self._refresh_timeline_locked()
                    break
            print(f"执行了{action}")
            self._execute(action)

    def _execute(self, action: ScheduledAction) -> None:
        if action.kind == "press":
            (key,) = action.payload
            pydirectinput.press(key)
            return

        if action.kind == "key_down":
            (key,) = action.payload
            pydirectinput.keyDown(key)
            return

        if action.kind == "key_up":
            (key,) = action.payload
            pydirectinput.keyUp(key)
            return

        if action.kind == "click":
            x, y = action.payload
            pydirectinput.click(x, y)
            return

        raise ValueError(f"未知的动作类型: {action.kind}")
