from __future__ import annotations

import ctypes
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

import operate
import ocr.ocr_utils as ocr_utils
import utils

GAME_TITLE = "BrownDust II"


def main() -> None:
    ctypes.windll.user32.SetProcessDPIAware()

    region = utils.get_window_region(GAME_TITLE)
    if not region:
        input(">>> 程序结束，按回车键关闭")
        raise SystemExit(1)

    config = utils.read_ini()
    begin_wait_time = config.getfloat("time", "begin_fish_wait_time", fallback=3)
    print(">>> 将实际执行一次背包清理")
    print(f">>> 请切换到游戏窗口，{begin_wait_time} 秒后开始")
    time.sleep(begin_wait_time)

    ocr_context = ocr_utils.build_ocr_context(config, region)
    with utils.DxCameraCapture(output_color="BGR") as sct:
        operate.clear_backpack(region, config, sct, ocr_context)

    print(">>> 背包清理测试完成")


if __name__ == "__main__":
    main()
