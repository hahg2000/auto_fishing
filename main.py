from __future__ import annotations

import configparser
import ctypes
import time
from typing import Type

import cv2
import pydirectinput

import qte_strategy as strategy
import utils
from utils import DxCameraCapture, Rect

ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II"
BITE_PIXEL_THRESHOLD = 8000
BITE_TIMEOUT_SECONDS = 15
CAST_HOLD_SECONDS = 0.38

QTE_STRATEGIES_MAP: dict[str, Type[strategy.BaseQTEStrategy]] = {
    "烟波湖": strategy.FrostStraitQTEStrategy,
    "浅岸": strategy.FrostStraitQTEStrategy,
    "寒霜海峡": strategy.FrostStraitQTEStrategy,
    "深渊巨口": strategy.AbyssMawQTEStrategy,
    "亚特兰蒂斯": strategy.FrostStraitQTEStrategy,
}


class FishingBot:
    def __init__(self, config: configparser.ConfigParser, region: Rect) -> None:
        self.config = config
        self.region = region
        self.hook_pos = utils.build_region_from_config(config, "hook", region)
        self.hook_yellow_range = utils.read_hsv_range(config, "hook", "hook")
        self.begin_fish_wait_time = utils.read_config_float(config, "time", "begin_fish_wait_time")
        self.round_end_wait_time = utils.read_config_float(config, "time", "round_end_wait_time")

    def cast_rod(self) -> None:
        pydirectinput.keyDown("space")
        time.sleep(CAST_HOLD_SECONDS)
        pydirectinput.keyUp("space")
        print(">>> 抛竿完成")

    def wait_for_bite(self, sct: DxCameraCapture) -> None:
        print(">>> 等待鱼上钩")
        wait_start_time = time.time()
        fail_num = 0

        while True:
            hook_frame = sct.grab(self.hook_pos)
            if hook_frame is None:
                continue

            hook_hsv = cv2.cvtColor(hook_frame, cv2.COLOR_BGR2HSV)
            hook_yellow = utils.create_color_mask(
                self.hook_yellow_range.lower,
                self.hook_yellow_range.upper,
                hook_hsv,
                is_dilate=False,
            )
            hook_yellow_pixel = cv2.countNonZero(hook_yellow)
            print(f"hook_yellow_pixel: {hook_yellow_pixel}")
            if hook_yellow_pixel > BITE_PIXEL_THRESHOLD:
                print(">>> 鱼上钩了！")
                pydirectinput.press("space")
                return

            if time.time() - wait_start_time <= BITE_TIMEOUT_SECONDS:
                continue

            print(">>> 突发情况，尝试恢复钓鱼状态")
            fail_num += 1
            wait_start_time = time.time()
            self.recover_from_timeout()

            # 预留后续做自动清背包或更复杂恢复逻辑
            if fail_num >= 9999:
                self.clear_backpack()
                fail_num = 0

    def recover_from_timeout(self) -> None:
        pydirectinput.keyDown("up")
        time.sleep(2)
        pydirectinput.keyUp("up")

        center_x, center_y = self.region.center
        pydirectinput.moveTo(center_x, center_y)
        time.sleep(0.2)
        pydirectinput.click()
        self.cast_rod()

    def clear_backpack(self) -> None:
        print(">>> 清理背包")
        pydirectinput.press("t")
        self._click_backpack_button("one_click_sale_left", "one_click_sale_top", delay=1)
        self._click_backpack_button("select_all_left", "select_all_top", delay=1)
        self._click_backpack_button("circle_check_left", "circle_check_top")
        self._click_backpack_button("dialog_confirm_left", "dialog_confirm_top", delay=0.5)
        self._click_backpack_button("quit_backpack_left", "quit_backpack_top", delay=0.5)

    def _click_backpack_button(self, left_key: str, top_key: str, *, delay: float = 0) -> None:
        if delay:
            time.sleep(delay)
        pos = utils.build_point_from_ratio(
            self.region,
            left_ratio=utils.read_config_float(self.config, "backpack", left_key),
            top_ratio=utils.read_config_float(self.config, "backpack", top_key),
        )
        pydirectinput.moveTo(*pos)
        pydirectinput.click()

    def choose_strategy(self) -> strategy.BaseQTEStrategy:
        print("可选钓鱼地点：")
        locations = list(QTE_STRATEGIES_MAP.keys())
        for idx, location in enumerate(locations, start=1):
            print(f"{idx}: {location}")

        selected_location = input(">>> 输入数字对应的钓鱼地点：")
        try:
            selected_index = int(selected_location) - 1
        except ValueError:
            selected_index = -1

        if selected_index in range(len(locations)):
            selected_name = locations[selected_index]
            print(f">>> 你选择了: {selected_name}")
            strategy_class = QTE_STRATEGIES_MAP[selected_name]
        else:
            print(">>> 选择无效，默认使用寒霜海峡策略")
            strategy_class = strategy.FrostStraitQTEStrategy

        return strategy_class(self.config, self.region)

    def run(self) -> None:
        qte_strategy = self.choose_strategy()
        time.sleep(self.begin_fish_wait_time)

        with DxCameraCapture(output_color="BGR") as sct:
            while True:
                self.cast_rod()
                self.wait_for_bite(sct)
                qte_strategy.play_qte(sct)
                print("================这轮的钓鱼结束================")
                time.sleep(self.round_end_wait_time)


def main() -> None:
    region = utils.get_window_region(GAME_TITLE)
    if not region:
        input(">>> 程序结束，按回车键关闭")
        raise SystemExit(1)

    config = utils.read_ini()
    FishingBot(config, region).run()


if __name__ == "__main__":
    main()
