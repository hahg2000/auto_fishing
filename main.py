import cv2
import mss
import numpy as np
import pydirectinput
import time
import win32gui
import ctypes
ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II" 

def get_window_region(window_title):
    """
    根据窗口标题找到窗口的 (left, top, width, height)
    """
    hwnd = win32gui.FindWindow(None, window_title)
    if not hwnd:
        print(f"错误: 未找到标题为 '{window_title}' 的窗口")
        return None
    
    # 获取窗口在屏幕上的坐标 (left, top, right, bottom)
    rect = win32gui.GetWindowRect(hwnd)
    x, y, right, bottom = rect
    w = right - x
    h = bottom - y
    
    # 返回 mss 需要的字典格式
    return {'left': x, 'top': y, 'width': w, 'height': h}

template = cv2.imread('exclamation_mark.png', cv2.IMREAD_GRAYSCALE) # 加载感叹号模板
region = get_window_region(GAME_TITLE)

hook_pos = {
    'left': region['left'] + int(region['width'] * 0.47),
    'top': region['top'] + int(region['height'] * 0.28),
    'width': int(region['width'] * (0.53 - 0.47)),
    'height': int(region['height'] * (0.39 - 0.28))
}

roi_pos = {
    'left': region['left'] + int(region['width'] * 0.37),
    'top': region['top'] + int(region['height'] * 0.86),
    'width': int(region['width'] * (0.65 - 0.37)),
    'height': int(region['height'] * (0.89 - 0.86))
}

# 如果屏幕色彩不同识别不出，可以改这里
lower_white = np.array([0, 0, 240]) 
upper_white = np.array([180, 50, 255])
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([40, 255, 255]) 

def wait_for_bite(sct):
    print("等待鱼上钩...")
    if not region: return
    wait_start_time = time.time()
    wait_end_time = time.time()
    fail_num = 0

    while True:
        hook_img = np.array(sct.grab(hook_pos))

        hook_img_gray = cv2.cvtColor(hook_img, cv2.COLOR_BGR2GRAY)
 
        res = cv2.matchTemplate(hook_img_gray, template, cv2.TM_CCOEFF_NORMED)
        # 71%的匹配度，可适当减少
        loc = np.where(res >= 0.71)
        if len(loc[0]) > 0: 
            print("鱼上钩了！") 
            # 收杆，进入QTE
            pydirectinput.press('space')
            return

        if fail_num > 3:
            print("背包满了")
            fail_num = 0
            clear_backpack()
            pydirectinput.press('space')
            continue

        wait_end_time = time.time()
        # 如果等待时间超过13秒，代表可能有突发情况
        if wait_end_time - wait_start_time > 13:
            print("突发情况")
            fail_num += 1

            wait_start_time = wait_end_time
            # 处理切换时间
            pydirectinput.keyDown('up')  
            time.sleep(2)
            pydirectinput.keyUp('up')

            # 点击屏幕
            finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)

            # 重新抛杆
            pydirectinput.press('space')
            continue
        
        # 取消注释来测试感叹号是否在框里
        # cv2.imshow("hook_img_gray", hook_img_gray)
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #   break 
 
def play_qte(sct):
    print("开始 QTE 战斗...")

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
                    pydirectinput.press('space')
        else:
            no_bar_frames += 1

            if no_bar_frames > 120:
                print("钓鱼结束")
                time.sleep(3.5)
                finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                break 

def finish_fishing(window_center_x, window_center_y):
    print(">>> 动作：点击鼠标左键确认")
    # 移动鼠标到窗口中心 (防止点歪)
    pydirectinput.moveTo(window_center_x, window_center_y)
    time.sleep(0.2)
    # 点击左键
    pydirectinput.click()

def cast_rod():
    print(">>> 动作：蓄力抛竿...")
    pydirectinput.keyDown('space')  # 按下不放
    time.sleep(0.38)                 # 持续 0.4 秒
    pydirectinput.keyUp('space')    # 松开
    print(">>> 动作：抛竿完成")

def clear_backpack():
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
            print("这轮的钓鱼结束")
            time.sleep(2)

if __name__ == "__main__": 
    main()