import cv2
import mss
import numpy as np
import pydirectinput
import time
import ctypes
import utils
import qte_strategy as strategy
ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II" 

region = utils.get_window_region(GAME_TITLE)
config = utils.read_ini()

QTE_STRATEGIES_MAP = {
    "烟波湖": strategy.FrostStraitQTEStrategy,
    "浅岸": strategy.FrostStraitQTEStrategy,
    "寒霜海峡": strategy.FrostStraitQTEStrategy,
    "深渊巨口": strategy.AbyssMawQTEStrategy,
    "亚特兰蒂斯": strategy.FrostStraitQTEStrategy,
}

# ================================== 读取配置 ==================================

hook_top_percent = utils.readConfigAndCastInt(config, "hook", "top_percent")
hook_bottom_percent = utils.readConfigAndCastInt(config, "hook", "bottom_percent")
hook_left_percent = utils.readConfigAndCastInt(config, "hook", "left_percent")
hook_right_percent = utils.readConfigAndCastInt(config, "hook", "right_percent")

hook_lower_yellow_hue = utils.readConfigAndCastInt(config, 'hook', 'hook_lower_yellow_hue')
hook_lower_yellow_saturation = utils.readConfigAndCastInt(config, 'hook', 'hook_lower_yellow_saturation')
hook_lower_yellow_value = utils.readConfigAndCastInt(config, 'hook', 'hook_lower_yellow_value')
hook_upper_yellow_hue = utils.readConfigAndCastInt(config, 'hook', 'hook_upper_yellow_hue')
hook_upper_yellow_saturation = utils.readConfigAndCastInt(config, 'hook', 'hook_upper_yellow_saturation')
hook_upper_yellow_value = utils.readConfigAndCastInt(config, 'hook', 'hook_upper_yellow_value')

lower_green_hue = utils.readConfigAndCastInt(config, "roi", "lower_green_hue")
lower_green_saturation = utils.readConfigAndCastInt(config, "roi", "lower_green_saturation")
lower_green_value = utils.readConfigAndCastInt(config, "roi", "lower_green_value")
upper_green_hue = utils.readConfigAndCastInt(config, "roi", "upper_green_hue")
upper_green_saturation = utils.readConfigAndCastInt(config, "roi", "upper_green_saturation")
upper_green_value = utils.readConfigAndCastInt(config, "roi", "upper_green_value")
lower_green = np.array([lower_green_hue, lower_green_saturation, lower_green_value])
upper_green = np.array([upper_green_hue, upper_green_saturation, upper_green_value])

if not region:
    input(">>> 程序结束，按回车键关闭")
    exit(1)

hook_pos = {
    "left": region["left"] + int(region["width"] * hook_left_percent / 100),
    "top": region["top"] + int(region["height"] * hook_top_percent / 100),
    "width": int(region["width"] * (hook_right_percent - hook_left_percent) / 100),
    "height": int(region["height"] * (hook_bottom_percent - hook_top_percent) / 100)
}

# ================================== 功能区 ==================================

def cast_rod():
    pydirectinput.keyDown("space")  # 按下不放
    time.sleep(0.38)                 # 持续 0.38 秒
    pydirectinput.keyUp("space")    # 松开
    print(">>> 抛竿完成")

def wait_for_bite(sct):
    print(">>> 等待鱼上钩")
    if not region: return
    wait_start_time = time.time()
    wait_end_time = time.time()
    fail_num = 0

    while True:
        hook_img = np.array(sct.grab(hook_pos))
        hook_hsv = cv2.cvtColor(hook_img, cv2.COLOR_BGRA2BGR)
        hook_hsv = cv2.cvtColor(hook_hsv, cv2.COLOR_BGR2HSV)
        hook_yellow = utils.create_color_mask([hook_lower_yellow_hue, hook_lower_yellow_saturation, hook_lower_yellow_value], 
                                              [hook_upper_yellow_hue, hook_upper_yellow_saturation, hook_upper_yellow_value], 
                                              hook_hsv, is_dilate=False)
        hook_yellow_pixel = cv2.countNonZero(hook_yellow) * 5
        if hook_yellow_pixel > 600: 
            print(">>> 鱼上钩了！") 
            # 收杆，进入QTE
            pydirectinput.press("space")
            return

        if fail_num > 2:
            print(">>> 背包满了")
            fail_num = 0
            clear_backpack()
            cast_rod()
            continue

        wait_end_time = time.time()
        # 如果等待时间超过10秒，代表可能有突发情况
        if wait_end_time - wait_start_time > 10:
            print(">>> 突发情况")
            fail_num += 1

            wait_start_time = wait_end_time
            # 处理切换时间
            pydirectinput.keyDown("up")  
            time.sleep(2)
            pydirectinput.keyUp("up")

            # 点击屏幕
            # 移动鼠标到窗口中心 (防止点歪)
            pydirectinput.moveTo(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
            time.sleep(0.2)
            # 点击左键
            pydirectinput.click()

            # 重新抛杆
            cast_rod()
            continue   
    
def clear_backpack():
    print(">>> 清理背包")
    # 打开背包
    pydirectinput.press("t")

    # 点击一键出售
    time.sleep(1)
    one_click_sale_left = int(region["left"] + region["width"] * float(config["backpack"]["one_click_sale_left"]))
    one_click_sale_top = int(region["top"] + region["height"] * float(config["backpack"]["one_click_sale_top"]))
    pydirectinput.moveTo(one_click_sale_left, one_click_sale_top)
    pydirectinput.click()

    # 点击全选
    time.sleep(1)
    select_all_left = int(region["left"] + region["width"] * float(config["backpack"]["select_all_left"]))
    select_all_top = int(region["top"] + region["height"] * float(config["backpack"]["select_all_top"]))
    pydirectinput.moveTo(select_all_left, select_all_top)
    pydirectinput.click()

    # 点击打钩按钮
    circle_check_left = int(region["left"] + region["width"] * float(config["backpack"]["circle_check_left"]))
    circle_check_top = int(region["top"] + region["height"] * float(config["backpack"]["circle_check_top"]))
    pydirectinput.moveTo(circle_check_left, circle_check_top)
    pydirectinput.click()

    # 点击确认按钮
    time.sleep(0.5)
    dialog_confirm_left = int(region["left"] + region["width"] * float(config["backpack"]["dialog_confirm_left"]))
    dialog_confirm_top = int(region["top"] + region["height"] * float(config["backpack"]["dialog_confirm_top"]))
    pydirectinput.moveTo(dialog_confirm_left, dialog_confirm_top)
    pydirectinput.click()

    # 退出背包
    time.sleep(0.5)
    quit_backpack_left = int(region["left"] + region["width"] * float(config["backpack"]["quit_backpack_left"]))
    quit_backpack_top = int(region["top"] + region["height"] * float(config["backpack"]["quit_backpack_top"]))
    pydirectinput.moveTo(quit_backpack_left, quit_backpack_top)
    pydirectinput.click()
    time.sleep(0.5)

def main():
    print("可选钓鱼地点：")
    for idx, location in enumerate(QTE_STRATEGIES_MAP.keys()):
        print(f"{idx + 1}: {location}")
    selected_location = input(">>> 输入数字对应的钓鱼地点：")
    
    if (int(selected_location) - 1) in range(len(QTE_STRATEGIES_MAP)):
        selected_location_name = list(QTE_STRATEGIES_MAP.keys())[int(selected_location) - 1]
        print(f">>> 你选择了: {selected_location_name}")
        QTEStrategyClass = QTE_STRATEGIES_MAP[selected_location_name]
    else:
        print(">>> 选择无效，默认使用寒霜海峡策略")
        QTEStrategyClass = strategy.FrostStraitQTEStrategy
        
    qte_strategy = QTEStrategyClass(config, region)
    
    time.sleep(float(config["time"]["begin_fish_wait_time"]))

    with mss.mss() as sct: 
        while True:
            # 1. 抛竿
            cast_rod()
            
            # 2. 等待上钩
            wait_for_bite(sct)
            
            # 3. QTE
            qte_strategy.play_qte(sct, region) 
            
            # 4. 结束
            print("================这轮的钓鱼结束================")
            time.sleep(float(config["time"]["round_end_wait_time"]))      

if __name__ == "__main__": 
    main()