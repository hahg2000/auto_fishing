import cv2
import mss
import numpy as np
import pydirectinput
import time
import ctypes
import utils
ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II" 

region = utils.get_window_region(GAME_TITLE)
config = utils.read_ini()

# ================================== 读取配置 ==================================
longest_keep_time = utils.readConfigAndCastInt(config, "time", "longest_keep_time")

roi_top_percent = utils.readConfigAndCastInt(config, "roi", "top_percent")
roi_bottom_percent = utils.readConfigAndCastInt(config, "roi", "bottom_percent")
roi_left_percent = utils.readConfigAndCastInt(config, "roi", "left_percent")
roi_right_percent = utils.readConfigAndCastInt(config, "roi", "right_percent")

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

lower_white_hue = utils.readConfigAndCastInt(config, 'roi', 'lower_white_hue')
lower_white_saturation = utils.readConfigAndCastInt(config, 'roi', 'lower_white_saturation')
lower_white_value = utils.readConfigAndCastInt(config, 'roi', 'lower_white_value')
upper_white_hue = utils.readConfigAndCastInt(config, 'roi', 'upper_white_hue')
upper_white_saturation = utils.readConfigAndCastInt(config, 'roi', 'upper_white_saturation')
upper_white_value = utils.readConfigAndCastInt(config, 'roi', 'upper_white_value')
lower_white = np.array([lower_white_hue, lower_white_saturation, lower_white_value]) 
upper_white = np.array([upper_white_hue, upper_white_saturation, upper_white_value])

lower_red_hue = utils.readConfigAndCastInt(config, "roi", "lower_red_hue")
lower_red_saturation = utils.readConfigAndCastInt(config, "roi", "lower_red_saturation")
lower_red_value = utils.readConfigAndCastInt(config, "roi", "lower_red_value")
upper_red_hue = utils.readConfigAndCastInt(config, "roi", "upper_red_hue")
upper_red_saturation = utils.readConfigAndCastInt(config, "roi", "upper_red_saturation")
upper_red_value = utils.readConfigAndCastInt(config, "roi", "upper_red_value")
lower_red = np.array([lower_red_hue, lower_red_saturation, lower_red_value])
upper_red = np.array([upper_red_hue, upper_red_saturation, upper_red_value])

lower_yellow_hue = utils.readConfigAndCastInt(config, "roi", "lower_yellow_hue")
lower_yellow_saturation = utils.readConfigAndCastInt(config, "roi", "lower_yellow_saturation")
lower_yellow_value = utils.readConfigAndCastInt(config, "roi", "lower_yellow_value")
upper_yellow_hue = utils.readConfigAndCastInt(config, "roi", "upper_yellow_hue")
upper_yellow_saturation = utils.readConfigAndCastInt(config, "roi", "upper_yellow_saturation")
upper_yellow_value = utils.readConfigAndCastInt(config, "roi", "upper_yellow_value")

lower_green_hue = utils.readConfigAndCastInt(config, "roi", "lower_green_hue")
lower_green_saturation = utils.readConfigAndCastInt(config, "roi", "lower_green_saturation")
lower_green_value = utils.readConfigAndCastInt(config, "roi", "lower_green_value")
upper_green_hue = utils.readConfigAndCastInt(config, "roi", "upper_green_hue")
upper_green_saturation = utils.readConfigAndCastInt(config, "roi", "upper_green_saturation")
upper_green_value = utils.readConfigAndCastInt(config, "roi", "upper_green_value")
lower_green = np.array([lower_green_hue, lower_green_saturation, lower_green_value])
upper_green = np.array([upper_green_hue, upper_green_saturation, upper_green_value])

lower_blue_hue = utils.readConfigAndCastInt(config, "roi", "lower_blue_hue")
lower_blue_saturation = utils.readConfigAndCastInt(config, "roi", "lower_blue_saturation")
lower_blue_value = utils.readConfigAndCastInt(config, "roi", "lower_blue_value")
upper_blue_hue = utils.readConfigAndCastInt(config, "roi", "upper_blue_hue")
upper_blue_saturation = utils.readConfigAndCastInt(config, "roi", "upper_blue_saturation")
upper_blue_value = utils.readConfigAndCastInt(config, "roi", "upper_blue_value")
lower_blue = np.array([lower_blue_hue, lower_blue_saturation, lower_blue_value])
upper_blue = np.array([upper_blue_hue, upper_blue_saturation, upper_blue_value])

time_lower_green_hue = utils.readConfigAndCastInt(config, 'roi', 'time_lower_green_hue')
time_lower_green_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_lower_green_saturation')
time_lower_green_value = utils.readConfigAndCastInt(config, 'roi', 'time_lower_green_value')
time_upper_green_hue = utils.readConfigAndCastInt(config, 'roi', 'time_upper_green_hue')
time_upper_green_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_upper_green_saturation')
time_upper_green_value = utils.readConfigAndCastInt(config, 'roi', 'time_upper_green_value')
time_lower_green = np.array([time_lower_green_hue, time_lower_green_saturation, time_lower_green_value])
time_upper_green = np.array([time_upper_green_hue, time_upper_green_saturation, time_upper_green_value])

time_lower_red_hue = utils.readConfigAndCastInt(config, 'roi', 'time_lower_red_hue')
time_lower_red_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_lower_red_saturation')
time_lower_red_value = utils.readConfigAndCastInt(config, 'roi', 'time_lower_red_value')
time_upper_red_hue = utils.readConfigAndCastInt(config, 'roi', 'time_upper_red_hue')
time_upper_red_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_upper_red_saturation')
time_upper_red_value = utils.readConfigAndCastInt(config, 'roi', 'time_upper_red_value')
time_lower_red = np.array([time_lower_red_hue, time_lower_red_saturation, time_lower_red_value])
time_upper_red = np.array([time_upper_red_hue, time_upper_red_saturation, time_upper_red_value])

time_top_percent = utils.readConfigAndCastInt(config, 'roi', 'time_top_percent')
time_bottom_percent = utils.readConfigAndCastInt(config, 'roi', 'time_bottom_percent')
time_left_percent = utils.readConfigAndCastInt(config, 'roi', 'time_left_percent')
time_right_percent = utils.readConfigAndCastInt(config, 'roi', 'time_right_percent')

if not region:
    input(">>> 程序结束，按回车键关闭")
    exit(1)

hook_pos = {
    "left": region["left"] + int(region["width"] * hook_left_percent / 100),
    "top": region["top"] + int(region["height"] * hook_top_percent / 100),
    "width": int(region["width"] * (hook_right_percent - hook_left_percent) / 100),
    "height": int(region["height"] * (hook_bottom_percent - hook_top_percent) / 100)
}

roi_pos = {
    "left": region["left"] + int(region["width"] * roi_left_percent / 100),
    "top": region["top"] + int(region["height"] * roi_top_percent / 100),
    "width": int(region["width"] * (roi_right_percent - roi_left_percent) / 100),
    "height": int(region["height"] * (roi_bottom_percent - roi_top_percent) / 100)
}

rot_pos = {
    "left": region["left"] + int(region["width"] * time_left_percent / 100),
    "top": region["top"] + int(region["height"] * time_top_percent / 100),
    "width": int(region["width"] * (time_right_percent - time_left_percent) / 100),
    "height": int(region["height"] * (time_bottom_percent - time_top_percent) / 100)
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
            finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)

            # 重新抛杆
            cast_rod()
            continue
 
def play_qte(sct):
    print(">>> 开始 QTE...")

    no_bar_frames = 0
    start_time = time.time()
    while time.time() - start_time < longest_keep_time:
        # 提取qte条的范围
        roi = np.array(sct.grab(roi_pos))
        rot = np.array(sct.grab(rot_pos))
        
        # MSS 默认是 BGRA
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR) 
        roi_hsv = cv2.cvtColor(roi_hsv, cv2.COLOR_BGR2HSV)
        rot_hsv = cv2.cvtColor(rot, cv2.COLOR_BGRA2BGR)
        rot_hsv = cv2.cvtColor(rot_hsv, cv2.COLOR_BGR2HSV)
        
        # 提取黄色区域
        mask_yellow = utils.create_color_mask([lower_yellow_hue, lower_yellow_saturation, lower_yellow_value], 
                                              [upper_yellow_hue, upper_yellow_saturation, upper_yellow_value], 
                                              roi_hsv)
        
        # 提取时间条的绿色和红色区域
        mask_green_time = utils.create_color_mask([time_lower_green_hue, time_lower_green_saturation, time_lower_green_value], 
                                                  [time_upper_green_hue, time_upper_green_saturation, time_upper_green_value], 
                                                  rot_hsv, is_dilate=False)
        mask_red_time = utils.create_color_mask([time_lower_red_hue, time_lower_red_saturation, time_lower_red_value], 
                                                [time_upper_red_hue, time_upper_red_saturation, time_upper_red_value], 
                                                rot_hsv, is_dilate=False)
        time_red_pixel_count = cv2.countNonZero(mask_red_time) * 20
        time_green_pixel_count = cv2.countNonZero(mask_green_time) * 10
        
        # 防止有其他有元素干扰
        if time_red_pixel_count + time_green_pixel_count > 1000: 
            no_bar_frames = 0
            # 找到光标位置
            mask_cursor = utils.create_color_mask(lower_white, upper_white, roi_hsv, is_dilate=False)
            col_sums = np.sum(mask_cursor, axis=0)
            # 找到白色像素最多的那一列的索引
            cursor_x = np.argmax(col_sums)
            
            #  如果画面里没有白色，cursor_x 可能是 0，需要防呆
            if np.max(col_sums) > 0: 
                check_y = roi.shape[0] // 2
                if mask_yellow[check_y, cursor_x]:
                    print(">>> 击中了黄色区域")
                    pydirectinput.press("space")
        else:
            no_bar_frames += 1

            if no_bar_frames > 30:
                print(">>> 钓鱼结束")
                time.sleep(float(config["time"]["fish_end_wait_time"]))
                finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                break 

def finish_fishing(window_center_x, window_center_y):
    # 移动鼠标到窗口中心 (防止点歪)
    pydirectinput.moveTo(window_center_x, window_center_y)
    time.sleep(0.2)
    # 点击左键
    pydirectinput.click()

def solve_ice_trouble(roi_hsv):
    """
    检测并解决冰冻状态
    :param roi_hsv: 当前QTE画面的 HSV 数据
    :return: True 如果检测到冰冻并执行了操作，False 如果无冰冻
    """
    mask = cv2.inRange(roi_hsv, lower_red, upper_red)
                
    # 计算红色像素数量，阈值设为 10 左右
    if cv2.countNonZero(mask) > 10: 
        print(">>> 检测到冰冻！正在破冰 (按空格)...")
        pydirectinput.press('space')
        # 为了防止按太快游戏不识别，给个极短的间隔
        time.sleep(0.05) 
        return True
    
    return False
    
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
    time.sleep(float(config["time"]["begin_fish_wait_time"]))
    try:
        with mss.mss() as sct: 
            while True:
                # 1. 抛竿
                cast_rod()
                
                # 2. 等待上钩
                wait_for_bite(sct)
                
                # 3. QTE
                play_qte(sct) 
                
                # 4. 结束
                print("================这轮的钓鱼结束================")
                time.sleep(float(config["time"]["round_end_wait_time"]))
    except BaseException:
        input(">>> 程序结束，按回车键关闭")

        

if __name__ == "__main__": 
    main()