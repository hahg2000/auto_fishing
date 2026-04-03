from __future__ import annotations

import configparser
import ctypes
import os
import time
import unicodedata
from typing import Type

import cv2
import pydirectinput

import qte_strategy as strategy
import utils
from ocr_engine import RapidOCREngine
from utils import DxCameraCapture, Rect

ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II"
BITE_PIXEL_THRESHOLD = 250
BITE_TIMEOUT_SECONDS = 15
CAST_HOLD_SECONDS = 0.38
DEFAULT_LOOP_SLEEP_SECONDS = 0.005

QTE_STRATEGIES_MAP: dict[str, Type[strategy.BaseQTEStrategy]] = {
    "烟波湖": strategy.FrostStraitQTEStrategy,
    "浅岸": strategy.FrostStraitQTEStrategy,
    "寒霜海峡": strategy.FrostStraitQTEStrategy,
    "深渊巨口": strategy.AbyssMawQTEStrategy,
    "亚特兰蒂斯": strategy.FrostStraitQTEStrategy,
}

LOCATION_MATCH_ALIASES: dict[str, tuple[str, ...]] = {
    "烟波湖": ("烟波湖", "烟波"),
    "浅岸": ("浅岸",),
    "寒霜海峡": ("寒霜海峡", "寒霜海", "寒霜"),
    "深渊巨口": ("深渊巨口", "深渊", "巨口"),
    "亚特兰蒂斯": ("亚特兰蒂斯", "亚特兰蒂", "特兰蒂斯"),
}


def normalize_ocr_text(text: str) -> str:
    normalized: list[str] = []
    for char in text:
        if char.isspace():
            continue
        category = unicodedata.category(char)
        if category.startswith("P") or category.startswith("S"):
            continue
        normalized.append(char.lower())
    return "".join(normalized)


class FishingBot:
    def __init__(self, config: configparser.ConfigParser, region: Rect) -> None:
        self.config = config
        self.region = region
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
        self.ocr_enabled = config.getboolean("ocr", "enabled", fallback=False)
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
        self.location_ocr_region = self._build_optional_ocr_region(
            left_key="location_left_percent",
            top_key="location_top_percent",
            right_key="location_right_percent",
            bottom_key="location_bottom_percent",
            fallback_region=Rect(0, 0, 100, 100),
        )
        self.ocr_engine: RapidOCREngine | None = None
        if self.ocr_enabled:
            try:
                self.ocr_engine = self._build_ocr_engine()
            except Exception as exc:
                print(f">>> OCR init failed: {exc}")
                self.ocr_enabled = False
        self._has_printed_hook_frame_size = True

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

    def _build_optional_ocr_region(
        self,
        *,
        left_key: str,
        top_key: str,
        right_key: str,
        bottom_key: str,
        fallback_region: Rect,
    ) -> Rect:
        if not all(
            self.config.has_option("ocr", key)
            for key in (left_key, top_key, right_key, bottom_key)
        ):
            return fallback_region

        return utils.build_region_from_percent(
            self.region,
            left_percent=self.config.getfloat("ocr", left_key),
            top_percent=self.config.getfloat("ocr", top_key),
            right_percent=self.config.getfloat("ocr", right_key),
            bottom_percent=self.config.getfloat("ocr", bottom_key),
        )

    def _resolve_ocr_resource_path(self, key: str) -> str | None:
        configured_value = self.config.get("ocr", key, fallback="").strip()
        if not configured_value:
            return None

        resolved_path = utils.get_resource_path(configured_value)
        if os.path.exists(resolved_path):
            return resolved_path

        return None

    def _build_ocr_engine(self) -> RapidOCREngine:
        det_model_path = self._resolve_ocr_resource_path("det_model_path")
        cls_model_path = self._resolve_ocr_resource_path("cls_model_path")
        rec_model_path = self._resolve_ocr_resource_path("rec_model_path")
        rec_keys_path = self._resolve_ocr_resource_path("rec_keys_path")
        return RapidOCREngine(
            det_model_path=det_model_path,
            cls_model_path=cls_model_path,
            rec_model_path=rec_model_path,
            rec_keys_path=rec_keys_path,
            use_cls=self.config.getboolean("ocr", "use_cls", fallback=False),
        )

    def _sort_ocr_results(self, results: list) -> None:
        results.sort(
            key=lambda item: (
                item.box.bounds[1] if item.box is not None else 0,
                item.box.bounds[0] if item.box is not None else 0,
            )
        )

    def _match_location_name(self, texts: list[str]) -> str | None:
        normalized_candidates = [normalize_ocr_text(text) for text in texts if normalize_ocr_text(text)]
        merged_candidate = normalize_ocr_text("".join(texts))
        if merged_candidate:
            normalized_candidates.append(merged_candidate)

        for location_name, aliases in LOCATION_MATCH_ALIASES.items():
            normalized_aliases = [normalize_ocr_text(location_name)]
            normalized_aliases.extend(normalize_ocr_text(alias) for alias in aliases)

            for alias in normalized_aliases:
                if not alias:
                    continue
                for candidate in normalized_candidates:
                    if alias in candidate:
                        return location_name
                    if len(candidate) >= 2 and candidate in alias:
                        return location_name
        return None

    def _detect_location_from_ocr(self, sct: DxCameraCapture) -> str | None:
        if not self.ocr_enabled or not self.auto_select_strategy or self.ocr_engine is None:
            return None

        frame = sct.grab(self.location_ocr_region)
        if frame is None:
            print(">>> OCR 截图失败，无法自动选择策略")
            return None
        
        # cv2.imshow("OCR Debug - Location Region", frame)
        # cv2.waitKey(1)
        
        try:
            results = self.ocr_engine.detect_and_recognize(frame)
            print(f">>> OCR 识别结果: {[item.text for item in results]}")
        except Exception as exc:
            print(f">>> OCR 执行失败: {exc}")
            return None

        self._sort_ocr_results(results)
        texts = [item.text.strip() for item in results if item.text.strip()]

        if not texts:
            print(">>> OCR 没有识别到任何文本，无法自动选择策略")
            return None

        matched_location = self._match_location_name(texts)
        if matched_location is None:
            print(">>> OCR 找到了文本但没有匹配的策略")
            return None

        print(f">>> 自动选择策略: {matched_location}")
        return matched_location

    def cast_rod(self) -> None:
        pydirectinput.keyDown("space")
        time.sleep(CAST_HOLD_SECONDS)
        pydirectinput.keyUp("space")
        print(">>> 抛竿完成")

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
                self.recover_from_timeout()

                # 预留后续做自动清背包或更复杂恢复逻辑
                if fail_num >= 9999:
                    self.clear_backpack()
                    fail_num = 0
                continue

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

    def choose_strategy(self, sct: DxCameraCapture) -> strategy.BaseQTEStrategy:
        auto_selected_name = self._detect_location_from_ocr(sct)
        if auto_selected_name is not None:
            strategy_class = QTE_STRATEGIES_MAP[auto_selected_name]
            return strategy_class(self.config, self.region)

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
        with DxCameraCapture(output_color="BGR") as sct:
            qte_strategy = self.choose_strategy(sct)
            time.sleep(self.begin_fish_wait_time)
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
