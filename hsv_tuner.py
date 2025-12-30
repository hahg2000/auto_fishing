import cv2
import numpy as np
import mss
import win32gui
import ctypes
ctypes.windll.user32.SetProcessDPIAware()

# === 配置区 ===
WINDOW_TITLE = "BrownDust II"  # 填入游戏实际标题
ROI_RATIO = [0.7, 0.9, 0.3, 0.7] # [y_start%, y_end%, x_start%, x_end%]
# 根据你的截图，我们只截取游戏窗口的中下方长条区域，减少干扰

def nothing(x):
    pass

def get_window_rect(title):
    hwnd = win32gui.FindWindow(None, title)
    if not hwnd: return None
    rect = win32gui.GetWindowRect(hwnd)
    return {'left': rect[0], 'top': rect[1], 'width': rect[2]-rect[0], 'height': rect[3]-rect[1]}

def start_tuner():
    region = get_window_rect(WINDOW_TITLE)
    if not region:
        print("未找到游戏窗口，请检查标题")
        return

    # 1. 进一步缩小区域到 QTE 条 (基于 ROI_RATIO)
    # 这样你就不用看整张图，只看那条蓝色的部分
    qte_region = {
        'left': region['left'] + int(region['width'] * ROI_RATIO[2]),
        'top': region['top'] + int(region['height'] * ROI_RATIO[0]),
        'width': int(region['width'] * (ROI_RATIO[3] - ROI_RATIO[2])),
        'height': int(region['height'] * (ROI_RATIO[1] - ROI_RATIO[0]))
    }

    cv2.namedWindow('HSV Tuner')
    
    # 2. 创建6个滑块
    cv2.createTrackbar('H Min', 'HSV Tuner', 0, 179, nothing)
    cv2.createTrackbar('H Max', 'HSV Tuner', 179, 179, nothing)
    cv2.createTrackbar('S Min', 'HSV Tuner', 0, 255, nothing)
    cv2.createTrackbar('S Max', 'HSV Tuner', 255, 255, nothing)
    cv2.createTrackbar('V Min', 'HSV Tuner', 0, 255, nothing)
    cv2.createTrackbar('V Max', 'HSV Tuner', 255, 255, nothing)

    # 设置默认值 (比如蓝色的预设)
    cv2.setTrackbarPos('H Min', 'HSV Tuner', 80)
    cv2.setTrackbarPos('H Max', 'HSV Tuner', 130)
    cv2.setTrackbarPos('S Min', 'HSV Tuner', 50)
    cv2.setTrackbarPos('V Min', 'HSV Tuner', 50)

    with mss.mss() as sct:
        while True:
            # 截图
            img = np.array(sct.grab(qte_region))
            img_display = img.copy() # 用于显示的副本
            
            # 转 HSV
            hsv = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
            hsv = cv2.cvtColor(hsv, cv2.COLOR_BGR2HSV)

            # 获取滑块当前值
            h_min = cv2.getTrackbarPos('H Min', 'HSV Tuner')
            h_max = cv2.getTrackbarPos('H Max', 'HSV Tuner')
            s_min = cv2.getTrackbarPos('S Min', 'HSV Tuner')
            s_max = cv2.getTrackbarPos('S Max', 'HSV Tuner')
            v_min = cv2.getTrackbarPos('V Min', 'HSV Tuner')
            v_max = cv2.getTrackbarPos('V Max', 'HSV Tuner')

            lower = np.array([h_min, s_min, v_min])
            upper = np.array([h_max, s_max, v_max])

            # 生成掩膜
            mask = cv2.inRange(hsv, lower, upper)
            
            # 将掩膜和原图合成，方便观察 (只保留选中的颜色，其他变黑)
            result = cv2.bitwise_and(img_display, img_display, mask=mask)

            # 堆叠显示：上面是原图，下面是提取效果
            # 如果窗口太高，可以横向堆叠 (np.hstack)
            final_stack = np.vstack((img_display, result))
            
            cv2.imshow('HSV Tuner', final_stack)
            
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break

    cv2.destroyAllWindows()
    # 打印最后选定的值，方便你复制
    print(f"最终调试结果: Lower=[{h_min}, {s_min}, {v_min}], Upper=[{h_max}, {s_max}, {v_max}]")

if __name__ == "__main__":
    start_tuner()