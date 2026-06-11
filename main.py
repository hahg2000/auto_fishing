from __future__ import annotations

import configparser
import ctypes
import time
from typing import Type

import cv2
import pydirectinput

import qte_strategy as strategy
import utils
import operate
import ocr.ocr_utils as ocr_utils
import ocr.ocr_service as ocr_service
from ocr.ocr_enum import DEFAULT_LOCATION, FishingLocation
from utils import DxCameraCapture, Rect

ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II"
BITE_PIXEL_THRESHOLD = 250
BITE_TIMEOUT_SECONDS = 15
DEFAULT_LOOP_SLEEP_SECONDS = 0.005

QTE_STRATEGIES_MAP: dict[FishingLocation, Type[strategy.BaseQTEStrategy]] = {
    FishingLocation.YANBO_LAKE: strategy.FrostStraitQTEStrategy,
    FishingLocation.SHALLOW_SHORE: strategy.FrostStraitQTEStrategy,
    FishingLocation.FROST_STRAIT: strategy.FrostStraitQTEStrategy,
    FishingLocation.ABYSS_MAW: strategy.AbyssMawQTEStrategy,
    FishingLocation.ATLANTIS: strategy.FrostStraitQTEStrategy,
}


class FishingBot:
    def __init__(self, config: configparser.ConfigParser, region: Rect, ocr_context: ocr_service.OCRContext) -> None:
        self.config = config
        self.region = region
        self.ocr_context = ocr_context
        self.selected_location_name = DEFAULT_LOCATION
        self.pixel_threshold_scale = utils.build_pixel_threshold_scale(config, region)
        self.hook_pos = utils.build_region_from_config(config, "hook", region)
        self.hook_yellow_range = utils.read_hsv_range(config, "hook", "hook")
        self.begin_fish_wait_time = utils.read_config_float(config, "time", "begin_fish_wait_time")
        self.round_end_wait_time = utils.read_config_float(config, "time", "round_end_wait_time")
        self.bite_pixel_threshold = utils.scale_pixel_threshold(
            BITE_PIXEL_THRESHOLD,
            self.pixel_threshold_scale,
        )
        self.loop_sleep_seconds = config.getfloat(
            "time",
            "loop_sleep_seconds",
            fallback=DEFAULT_LOOP_SLEEP_SECONDS,
        )
        self.ocr_debug_once_on_start = config.getboolean(
            "ocr",
            "debug_once_on_start",
            fallback=True,
        )
        self.auto_select_strategy = config.getboolean(
            "ocr",
            "auto_select_strategy",
            fallback=True,
        )
        self.change_location_keyword = config.get("ocr", "change_location_keyword", fallback="小时").strip()

        print(f">>> 当前游戏窗口截图尺寸: {region.width} x {region.height}")
        print(
            ">>> 像素阈值缩放倍率: "
            f"{self.pixel_threshold_scale.factor:.4f} "
            f"(参考窗口: {self.pixel_threshold_scale.reference_width} x "
            f"{self.pixel_threshold_scale.reference_height})"
        )
        print(f">>> 上钩黄色像素阈值: {BITE_PIXEL_THRESHOLD} -> {self.bite_pixel_threshold}")


    def _sleep_loop(self) -> None:
        time.sleep(self.loop_sleep_seconds)


    def wait_for_bite(self, sct: DxCameraCapture) -> None:
        print(">>> 等待鱼上钩")
        wait_start_time = time.monotonic()
        fail_num = 0

        while True:
            now = time.monotonic()
            if now - wait_start_time > BITE_TIMEOUT_SECONDS:
                print(">>> 突发情况，尝试恢复钓鱼状态")
                fail_num += 1
                wait_start_time = now
                operate.recover_from_timeout(self.region)

            if now - wait_start_time < 0.5 and ocr_service.check_backpack_if_full(sct, self.ocr_context):  
                operate.clear_backpack(self.region, self.config, sct, self.ocr_context)
                operate.cast_rod()
                
            hook_frame = sct.grab(self.hook_pos)
            if hook_frame is None:
                self._sleep_loop()
                continue
            
            hook_hsv = cv2.cvtColor(hook_frame, cv2.COLOR_BGR2HSV)
            hook_yellow = utils.create_color_mask(
                self.hook_yellow_range.lower,
                self.hook_yellow_range.upper,
                hook_hsv,
                is_dilate=False,
            )
            hook_yellow_pixel = cv2.countNonZero(hook_yellow)

            if hook_yellow_pixel > self.bite_pixel_threshold:
                print(">>> 鱼上钩了！")
                pydirectinput.press("space")
                return 
            self._sleep_loop()


    def choose_strategy(self, sct: DxCameraCapture) -> strategy.BaseQTEStrategy:
        auto_selected_name = ocr_service.detect_location_from_ocr(sct, self.ocr_context, self.auto_select_strategy)
        if auto_selected_name is not None:
            strategy_class = QTE_STRATEGIES_MAP[auto_selected_name]
            self.selected_location_name = auto_selected_name
            return strategy_class(self.config, self.region)

        print("可选钓鱼地点：")
        locations = list(QTE_STRATEGIES_MAP.keys())
        for idx, location in enumerate(locations, start=1):
            print(f"{idx}: {location.value}")

        selected_location = input(">>> 输入数字对应的钓鱼地点：")
        try:
            selected_index = int(selected_location) - 1
        except ValueError:
            selected_index = -1

        if selected_index in range(len(locations)):
            selected_name = locations[selected_index]
            print(f">>> 你选择了: {selected_name.value}")
            self.selected_location_name = selected_name
            strategy_class = QTE_STRATEGIES_MAP[selected_name]
        else:
            print(">>> 选择无效，默认使用寒霜海峡策略")
            self.selected_location_name = FishingLocation.FROST_STRAIT
            strategy_class = QTE_STRATEGIES_MAP[self.selected_location_name]

        return strategy_class(self.config, self.region)

    def run(self) -> None:
        with DxCameraCapture(output_color="BGR") as sct:
            qte_strategy = self.choose_strategy(sct)
            time.sleep(self.begin_fish_wait_time)
            while True:
                if ocr_service.check_if_time_to_change_location(sct, self.ocr_context):
                    operate.change_location(sct, self.ocr_context, self.selected_location_name)
                    
                operate.cast_rod()
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
    
    ocr_context = ocr_utils.build_ocr_context(config, region)
    
    FishingBot(config, region, ocr_context).run()


if __name__ == "__main__":
    main()
