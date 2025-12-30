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
HOOK_ROI = {'top': 300, 'left': 800, 'width': 100, 'height': 100} # 感叹号区域
BAR_ROI = {'top': 800, 'left': 600, 'width': 600, 'height': 50}  # 下方长方形条区域
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

        # hook_test = img[int(height*0.3):int(height*0.4 ), int(width*0.45): int(width*0.55)]
        # hook_img_gray = cv2.cvtColor(hook_img, cv2.COLOR_BGR2GRAY) 

        # template_gray = cv2.cvtColor(np.asarray( template), cv2.COLOR_BGRA2GRAY)
    
        # cv2.imshow("hook_img" , hook_img_gray) 
        # cv2.imshow("img", template) 
        # printimg.size()), gray.size())  
        # print(gray.size, np .array(templ ate).size ) 
        w, h = template.shape[::-1]
        res = cv2.matchTemplate(hook_img_gray, template, cv2.TM_CCOEFF_NORMED)
        # res = np.array([0])  
        loc = np.where(res >= 0.73) # 80% 匹配度 
 
        # for pt in zip(*loc[::-1]): 
        #     cv2.rectangle(img, pt, (pt[0] + w, pt[1] + h), (0,0,255), 2)

        # print(loc[::-1]) 
        if len(loc[0]) > 0:
            print("鱼上钩了！")
            time.sleep(0.5) # 等待UI切换
            pydirectinput.press('space') # 收杆，进入QTE
            # time.sleep(0.5) # 等待UI切换
            return
        # cv2.imshow("img" , img) 
        # cv2.imshow("img" , img)           
        # if cv2.waitKey(1) & 0xFF == ord('q'):
        #     break 
 
def play_qte(sct):
    """阶段2：处理QTE"""
    print("开始 QTE 战斗...")
    no_bar_frames = 0
    # 定义 HSV 颜色范围 (需要你需要用截图工具取色来确定具体的数值)
    # 这里只是示例值 
    # lower_blue = np.array([100, 50, 50])
    # upper_blue = np.array([130, 255, 255])
    # lower_yellow = np.array([20, 100, 100])
    # upper_yellow = np.array([30, 255, 255])

    start_time = time.time()
    while time.time() - start_time < 15: # 假设最大时长15秒
        # 提取qte条的范围
        img = np.array(sct.grab(region))
        height, width = img.shape[:2]  
        roi = img[int(height*0.86):int(height*0.89), int(width*0.37):int(width*0.65)]
        roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR) # MSS 默认是 BGRA
        roi_hsv = cv2.cvtColor(roi_hsv, cv2.COLOR_BGR2HSV)
        
        # 1. 提取有效区域 (蓝/黄)
        mask_blue = cv2.inRange(roi_hsv, lower_blue, upper_blue)
        mask_yellow = cv2.inRange(roi_hsv, lower_yellow, upper_yellow)
        kernel = np.ones((5, 5), np.uint8) # 5x5 的卷积核
        mask_blue = cv2.dilate(mask_blue, kernel, iterations=2)
        mask_yellow = cv2.dilate(mask_yellow, kernel, iterations=2)

        # valid_zone = cv2.bitwise_or(mask_blue, mask_yellow)
        mask_yellow_pixel_count = cv2.countNonZero(mask_yellow) * 12 
        mask_blue_pixel_count = cv2.countNonZero(mask_blue) * 0.2
        pixel_count = mask_blue_pixel_count + mask_yellow_pixel_count
        # print(pixel_count)
        if pixel_count > 7000:  
            no_bar_frames = 0
            # 2. 找到光标位置 (假设光标是白色的)
            mask_cursor = cv2.inRange(roi_hsv, lower_white, upper_white)
            col_sums = np.sum(mask_cursor, axis=0)
            cursor_x = np.argmax(col_sums) # 找到白色像素最多的那一列的索引
            #  如果画面里没有白色，cursor_x 可能是 0，需要防呆
            if np.max(col_sums) == 0:
                cursor_found = False
            else:
                cursor_found = True
                # 画出光标位置 (红色竖线) 用于调试
                # cv2.line(roi, (cursor_x, 0), (cursor_x, roi.shape[0]), (0, 0, 255), 2)
                if mask_yellow[roi.shape[0]//2, cursor_x] == 255:
                    pydirectinput.press('space')
                    status = "PERFECT (Yellow)"
                    time.sleep(0.5)  
        else:
            no_bar_frames += 1

            if no_bar_frames > 20:
                time.sleep(2)
                print("钓鱼结束")
                finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                break 
        # if cursor_found:
        # 获取光标所在位置的 mask 值 (255 表示在区域内，0 表示不在)
        # 这里的逻辑是：如果光标的 x 坐标对应的 mask 是白色的，就说明撞上了 
        
        # for i in range(0, height):
            # 检查黄色 (优先)
        # if mask_yellow[roi.shape[0]//2, cursor_x] == 255:
        #     pydirectinput.press('space')
        #     status = "PERFECT (Yellow)"
            # time.sleep(0.5)    
            # 检查蓝色 
            # elif mask_blue[roi.shape[0]//2, cursor_x] == 255:
                # pydirectinput.press('space')
                # status = "GOOD (Blue)"

            # print(f"当前判定状态: {status}")
        # 更好的方法是：如果光标一直在动，可以用背景减除法
        # gray = cv2.cvtColor(img, cv2.COLOR_BGRA2GRAY)
        # _, cursor_mask = cv2.threshold(gray, 240, 255, cv2.THRESH_BINARY) # 提取高亮光标
        
        # 获取光标重心
        # M = cv2.moments(cursor_mask)
        # if M["m00"] != 0:
            # cX = int(M["m10"] / M["m00"])
            # cY = int(M["m01"] / M["m00"])
            
            # 3. 碰撞检测：光标坐标是否在有效区域mask内 (像素值是否为255)
            # 注意边界检查
            # if mask_yellow[cY, cX] == 255:
                # pydirectinput.press('space')
                # 稍微暂停防止按键过快，或者根据游戏机制调整
                # time.sleep(0.05) 
        
        # 显示调试窗口 (按q退出)
        # cv2.imshow('roi', roi)
        # if cv2.waitKey(20) & 0xFF == ord('q'):
            # break

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
    time.sleep(0.5)                 # 持续 1 秒
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