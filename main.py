import cv2
import mss
import numpy as np
import pydirectinput
import time
import ctypes
import utils
ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II" 

# 加载感叹号模板
# template = cv2.imread('exclamation_mark.png', cv2.IMREAD_GRAYSCALE)
image_path = utils.get_resource_path('exclamation_mark.png')
template = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
region = utils.get_window_region(GAME_TITLE)
config = utils.read_ini()

roi_top_percent = int(config['roi']['top_percent'])
roi_bottom_percent = int(config['roi']['bottom_percent'])
roi_left_percent = int(config['roi']['left_percent'])
roi_right_percent = int(config['roi']['right_percent'])

hook_top_percent = int(config['hook']['top_percent'])
hook_bottom_percent = int(config['hook']['bottom_percent'])
hook_left_percent = int(config['hook']['left_percent'])
hook_right_percent = int(config['hook']['right_percent'])

lower_yellow_hue = int(config['roi']['lower_yellow_hue'])
lower_yellow_saturation = int(config['roi']['lower_yellow_saturation'])
lower_yellow_value = int(config['roi']['lower_yellow_value'])
upper_yellow_hue = int(config['roi']['upper_yellow_hue'])
upper_yellow_saturation = int(config['roi']['upper_yellow_saturation'])
upper_yellow_value = int(config['roi']['upper_yellow_value'])
lower_yellow = np.array([lower_yellow_hue, lower_yellow_saturation, lower_yellow_value])
upper_yellow = np.array([upper_yellow_hue, upper_yellow_saturation, upper_yellow_value])
            
hook_pos = {
    'left': region['left'] + int(region['width'] * hook_left_percent / 100),
    'top': region['top'] + int(region['height'] * hook_top_percent / 100),
    'width': int(region['width'] * (hook_right_percent - hook_left_percent) / 100),
    'height': int(region['height'] * (hook_bottom_percent - hook_top_percent) / 100)
}

roi_pos = {
    'left': region['left'] + int(region['width'] * roi_left_percent / 100),
    'top': region['top'] + int(region['height'] * roi_top_percent / 100),
    'width': int(region['width'] * (roi_right_percent - roi_left_percent) / 100),
    'height': int(region['height'] * (roi_bottom_percent - roi_top_percent) / 100)
}

# 如果屏幕色彩不同识别不出，可以改这里
lower_white = np.array([0, 0, 240]) 
upper_white = np.array([180, 50, 255])
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([40, 255, 255]) 

def wait_for_bite(sct):
    print(">>> 等待鱼上钩")
    if not region: return
    wait_start_time = time.time()
    wait_end_time = time.time()
    fail_num = 0

    while True:
        hook_img = np.array(sct.grab(hook_pos))

        hook_img_gray = cv2.cvtColor(hook_img, cv2.COLOR_BGR2GRAY)
 
        res = cv2.matchTemplate(hook_img_gray, template, cv2.TM_CCOEFF_NORMED)
        # 60%的匹配度，可适当减少
        loc = np.where(res >= 0.60)
        if len(loc[0]) > 0: 
            print(">>> 鱼上钩了！") 
            # 收杆，进入QTE
            pydirectinput.press('space')
            return

        if fail_num > 3:
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
            pydirectinput.keyDown('up')  
            time.sleep(2)
            pydirectinput.keyUp('up')

            # 点击屏幕
            finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)

            # 重新抛杆
            cast_rod()
            continue
 
def play_qte(sct):
    print(">>> 开始 QTE...")

    no_bar_frames = 0
    start_time = time.time()
    # 最大时长15秒
    while time.time() - start_time < 15:
        # 提取qte条的范围
        roi = np.array(sct.grab(roi_pos))
        
        # MSS 默认是 BGRA
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR) 
        roi_hsv = cv2.cvtColor(roi_hsv, cv2.COLOR_BGR2HSV)
        
        # 提取黄色区域
        mask_yellow = cv2.inRange(roi_hsv, lower_yellow, upper_yellow)
        # 7x7 的卷积核
        kernel = np.ones((7, 7), np.uint8) 
        mask_yellow = cv2.dilate(mask_yellow, kernel, iterations=2) 

        pixel_count = cv2.countNonZero(mask_yellow) * 25 

        # 防止有其他有元素干扰
        if pixel_count > 8000:  
            no_bar_frames = 0
            # 找到光标位置
            mask_cursor = cv2.inRange(roi_hsv, lower_white, upper_white)
            col_sums = np.sum(mask_cursor, axis=0)
            # 找到白色像素最多的那一列的索引
            cursor_x = np.argmax(col_sums) 
            #  如果画面里没有白色，cursor_x 可能是 0，需要防呆
            if np.max(col_sums) != 0: 
                # 边界处理，向前向后5个像素都还是完美区域
                check_y = roi.shape[0] // 2
                if mask_yellow[check_y, cursor_x]:
                    print(">>> 击中了黄色区域")
                    pydirectinput.press('space')
        else:
            no_bar_frames += 1

            if no_bar_frames > 130:
                print(">>> 钓鱼结束")
                time.sleep(3.5)
                finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                break 

def finish_fishing(window_center_x, window_center_y):
    # 移动鼠标到窗口中心 (防止点歪)
    pydirectinput.moveTo(window_center_x, window_center_y)
    time.sleep(0.2)
    # 点击左键
    pydirectinput.click()

def cast_rod():
    pydirectinput.keyDown('space')  # 按下不放
    time.sleep(0.38)                 # 持续 0.38 秒
    pydirectinput.keyUp('space')    # 松开
    print(">>> 抛竿完成")

def clear_backpack():
    print(">>> 清理背包")
    # 打开背包
    pydirectinput.press('t')

    # 点击一键出售
    time.sleep(1)
    pydirectinput.moveTo(int(region["left"] + region["width"] * 0.87), int(region["top"] + region["height"] * 0.92))
    pydirectinput.click()

    # 点击全选
    pydirectinput.moveTo(int(region["left"] + region["width"] * 0.82), int(region["top"] + region["height"] * 0.92))
    pydirectinput.click()

    # 点击打钩按钮
    pydirectinput.moveTo(int(region["left"] + region["width"] * 0.92), int(region["top"] + region["height"] * 0.92))
    pydirectinput.click()

    # 点击确认按钮
    time.sleep(0.5)
    pydirectinput.moveTo(int(region["left"] + region["width"] * 0.57), int(region["top"] + region["height"] * 0.61))
    pydirectinput.click()

    # 退出背包
    time.sleep(0.5)
    pydirectinput.moveTo(int(region["left"] + region["width"] * 0.1), int(region["top"] + region["height"] * 0.12))
    pydirectinput.click()
    time.sleep(0.5)

def main():
    time.sleep(3)
    
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
            time.sleep(2)

if __name__ == "__main__": 
    main()