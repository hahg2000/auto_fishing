from __future__ import annotations

import ctypes
import time

import cv2
import pydirectinput

from actions import ActionExecutor
from capture import WindowCaptureBuffer
from engine import AutoFishingEngine
import qte_strategy as strategy
import utils
import win32gui


ctypes.windll.user32.SetProcessDPIAware()

GAME_TITLE = "BrownDust II"

config = utils.read_ini()
# region = utils.get_window_region(GAME_TITLE)

QTE_STRATEGIES_MAP = {
    "烟波湖": strategy.FrostStraitQTEStrategy,
    "浅岸": strategy.AbyssMawQTEStrategy,
    "寒霜海峡": strategy.FrostStraitQTEStrategy,
    "深渊巨口": strategy.AbyssMawQTEStrategy,
    "亚特兰蒂斯": strategy.FrostStraitQTEStrategy,
}


def clear_backpack() -> None:
    # 保留旧接口，方便测试脚本调用
    # if not region:
    #     raise RuntimeError("Game window not found.")

    # print(">>> Clear backpack")
    # pydirectinput.press("t")

    # time.sleep(1)
    # one_click_sale = utils.relative_point(
    #     region,
    #     float(config["backpack"]["one_click_sale_left"]),
    #     float(config["backpack"]["one_click_sale_top"]),
    # )
    # pydirectinput.click(*one_click_sale)

    # time.sleep(1)
    # select_all = utils.relative_point(
    #     region,
    #     float(config["backpack"]["select_all_left"]),
    #     float(config["backpack"]["select_all_top"]),
    # )
    # pydirectinput.click(*select_all)

    # time.sleep(1)
    # circle_check = utils.relative_point(
    #     region,
    #     float(config["backpack"]["circle_check_left"]),
    #     float(config["backpack"]["circle_check_top"]),
    # )
    # pydirectinput.click(*circle_check)

    # time.sleep(1)
    # dialog_confirm = utils.relative_point(
    #     region,
    #     float(config["backpack"]["dialog_confirm_left"]),
    #     float(config["backpack"]["dialog_confirm_top"]),
    # )
    # pydirectinput.click(*dialog_confirm)

    # time.sleep(1)
    # quit_backpack = utils.relative_point(
    #     region,
    #     float(config["backpack"]["quit_backpack_left"]),
    #     float(config["backpack"]["quit_backpack_top"]),
    # )
    # pydirectinput.click(*quit_backpack)
    time.sleep(1)


def select_strategy_class():
    print("可选钓鱼地点：")
    for index, location in enumerate(QTE_STRATEGIES_MAP.keys(), start=1):
        print(f"{index}: {location}")

    selected_location = input(">>> 请输入地点编号: ")
    try:
        selected_index = int(selected_location) - 1
    except ValueError:
        selected_index = -1

    if selected_index not in range(len(QTE_STRATEGIES_MAP)):
        print(">>> 非法选择，默认寒霜海峡")
        return strategy.FrostStraitQTEStrategy

    selected_name = list(QTE_STRATEGIES_MAP.keys())[selected_index]
    print(f">>> 已选择: {selected_name}")
    return QTE_STRATEGIES_MAP[selected_name]


def main() -> int:
    hwnd = win32gui.FindWindow(None, GAME_TITLE)
    
    # 选择 QTE 策略
    strategy_class = select_strategy_class()

    # 初始化三层组件：采集、引擎、动作执行
    capture = WindowCaptureBuffer(GAME_TITLE)
    actions = ActionExecutor()
    debug_enable = utils.read_config_bool(config, "debug", "enable", False)
    debug_show_windows = utils.read_config_bool(config, "debug", "show_windows", True)
    debug_show_qte_windows = utils.read_config_bool(config, "debug", "show_qte_windows", True)
    debug_show_hook_windows = utils.read_config_bool(config, "debug", "show_hook_windows", True)
    stats_interval = utils.read_config_float(config, "debug", "stats_interval", 1.0)
    engine = AutoFishingEngine(
        config=config,
        capture=capture,
        actions=actions,
        strategy=strategy_class(config, hwnd),
        debug=debug_enable,
        debug_show_windows=debug_show_windows,
        debug_show_windows_config=(debug_show_hook_windows, debug_show_qte_windows),
        stats_interval=stats_interval,
        hwnd=hwnd,
    )

    actions.start()
    engine.start()

    print(">>> Auto fishing started, waiting for frames...")
    try:
        # 注意：capture.start 是阻塞调用
        capture.start()
    finally:
        engine.stop()
        actions.stop()       
        cv2.destroyAllWindows()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
