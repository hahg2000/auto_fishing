import cv2
import mss
import numpy as np
import pydirectinput
import time
import get_window_region
import ctypes
ctypes.windll.user32.SetProcessDPIAware()
GAME_TITLE = "BrownDust II" 

# 屏幕区域定义 (需要根据你的屏幕分辨率和游戏窗口位置调整)
# 格式: {'top': y, 'left': x, 'width': w, 'height': h}
template = cv2.imread('exclamation_mark.png', cv2.IMREAD_GRAYSCALE) # 加载感叹号模板
region = get_window_region.get_window_region(GAME_TITLE)

lower_white = np.array([0, 0, 240]) 
upper_white = np.array([180, 50, 255])
lower_yellow = np.array([20, 100, 100])
upper_yellow = np.array([40, 255, 255]) 
lower_blue = np.array([80, 100, 100])
upper_blue = np.array([120, 255, 255])

def wait_for_bite(sct):
    """阶段1：等待上钩"""
    print("等待鱼上钩...")
    if not region: return

    if template is None:
        return 
     
    while True:
        img = np.array(sct.grab(region))
        height, width = img.shape[:2]

        hook_img = img[int(height*0.3):int(height*0.4), int(width*0.47): int(width*0.53)]
        hook_img_gray = cv2.cvtColor(hook_img, cv2.COLOR_BGR2GRAY)

        res = cv2.matchTemplate(hook_img_gray, template, cv2.TM_CCOEFF_NORMED)
        # res = np.array([0])  
        loc = np.where(res >= 0.73) # 80% 匹配度 

        if len(loc[0]) > 0:
            print("鱼上钩了！")
            pydirectinput.press('space') # 收杆，进入QTE
            # time.sleep(0.5) # 等待UI切换
            return
        cv2.imshow("img" , hook_img_gray) 
        # cv2.imshow("img" , img)           
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break 
 
def play_qte(sct):
    """阶段2：处理QTE"""
    print("开始 QTE 战斗...")
    bar_roi = {
        'left': region['left'] + int(region['width'] * 0.37),
        'top': region['top'] + int(region['height'] * 0.86),
        'width': int(region['width'] * (0.65 - 0.37)),
        'height': int(region['height'] * (0.89 - 0.86))
    }

    no_bar_frames = 0
    start_time = time.time()
    while time.time() - start_time < 15: # 假设最大时长15秒
        # 提取qte条的范围
        # img = np.array(sct.grab(region))
        roi = np.array(sct.grab(bar_roi))
        # roi = img[int(height*0.86):int(height*0.89), int(width*0.37):int(width*0.65)]
        # height, width = img.shape[:2]
        
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR) # MSS 默认是 BGRA
        roi_hsv = cv2.cvtColor(roi_hsv, cv2.COLOR_BGR2HSV)
        
        # 1. 提取有效区域 (蓝/黄)
        mask_yellow = cv2.inRange(roi_hsv, lower_yellow, upper_yellow)
        kernel = np.ones((5, 5), np.uint8) # 5x5 的卷积核
        mask_yellow = cv2.dilate(mask_yellow, kernel, iterations=2) 

        pixel_count = cv2.countNonZero(mask_yellow) * 20 
        # print(pixel_count)
        if pixel_count > 8000:  
            no_bar_frames = 0
            # 2. 找到光标位置 (假设光标是白色的)
            # mask_cursor = cv2.inRange(roi_hsv, lower_white, upper_white)
            gray = cv2.cvtColor(roi, cv2.COLOR_BGRA2GRAY)
            _, mask_cursor = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY)
            col_sums = np.sum(mask_cursor, axis=0)
            cursor_x = np.argmax(col_sums) # 找到白色像素最多的那一列的索引
            #  如果画面里没有白色，cursor_x 可能是 0，需要防呆
            if np.max(col_sums) == 0:
                cursor_found = False
            else:
                cursor_found = True
                # 画出光标位置 (红色竖线) 用于调试 
                # cv2.line(roi, (cursor_x, 0), (cursor_x, roi.shape[0]), (0, 0, 255), 2)
                if mask_yellow[roi.shape[0]//2, cursor_x + 5] == 255 or mask_yellow[roi.shape[0]//2, cursor_x - 5] == 255:
                    pydirectinput.press('space')
                    status = "PERFECT (Yellow)"
                    time.sleep(0.5)  
        else:
            no_bar_frames += 1

            if no_bar_frames > 20:
                print("钓鱼结束")
                time.sleep(3)
                finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                break 
        # 更好的方法是：如果光标一直在动，可以用背景减除法
        # gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        # _, cursor_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY) # 提取高亮 光标
        
        # 显示调试窗口 (按q退出)
        # cv2.imshow('roi', mask_cursor)
        # if cv2.waitKey(20) & 0xFF == ord('q'):
        #     break

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
    time.sleep(0.4)                 # 持续 1 秒
    pydirectinput.keyUp('space')    # 松开
    print(">>> 动作：抛竿完成")

def main():
    time.sleep(2)
    with mss.mss() as sct: 
        while True:
            # 1. 抛竿
            # pydirectinput.press('space') 
            cast_rod()
            
            # 2. 等待上钩
            wait_for_bite(sct)
            
            # 3. QTE
            play_qte(sct) 
            
        
            print("这轮的钓鱼结束")
            time.sleep(2) # 休息一下再下一杆

            # if cv2.waitKey(1) & 0xFF == ord('q'):
            #     break

if __name__ == "__main__": 
    main()