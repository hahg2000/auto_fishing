import cv2
import numpy as np

def analyze_fishing_bar(image_path):
    # 1. 读取图片
    img = cv2.imread(image_path)
    if img is None:
        print("未找到图片")
        return

    # 截取 QTE 条的大致区域 (ROI)
    # 根据截图，我们主要关注下方那个深色胶囊形状的区域
    # 注意：这里的坐标是基于你上传的截图估算的，实战中需要针对全屏截图调整 y1, y2, x1, x2
    # 获取图片的长宽 格式为（长：宽：颜色宽度）
    height, width = img.shape[:2]
    roi = img[int(height*0.55):int(height*0.85), int(width*0.2):int(width*0.9)]
    
    # 转为 HSV 颜色空间
    hsv = cv2.cvtColor(roi, cv2.COLOR_BGR2HSV)

    # ==============================
    # 步骤 A: 识别光标 (白色)
    # ==============================
    # 白色特征：饱和度(S)低，亮度(V)极高
    lower_white = np.array([0, 0, 240]) 
    upper_white = np.array([180, 50, 255])
    mask_cursor = cv2.inRange(hsv, lower_white, upper_white)
    # cv2.imshow("Mask Cursor", mask_cursor)

    # 找到光标的 X 坐标 (通过计算列像素之和，最亮的那一列就是光标中心)
    col_sums = np.sum(mask_cursor, axis=0)
    cursor_x = np.argmax(col_sums) # 找到白色像素最多的那一列的索引
    
    # 如果画面里没有白色，cursor_x 可能是 0，需要防呆
    if np.max(col_sums) == 0:
        cursor_found = False
        print("未检测到光标")
    else:
        cursor_found = True
        # 画出光标位置 (红色竖线) 用于调试
        cv2.line(roi, (cursor_x, 0), (cursor_x, roi.shape[0]), (0, 0, 255), 2)

    # ==============================
    # 步骤 B: 识别黄色 (完美区域)
    # ==============================
    lower_yellow = np.array([20, 100, 100])
    upper_yellow = np.array([40, 255, 255])
    mask_yellow = cv2.inRange(hsv, lower_yellow, upper_yellow)

    # ==============================
    # 步骤 C: 识别蓝色 (普通区域) - 重点处理斜纹
    # ==============================
    # 蓝色的 HSV 范围 (根据截图推测是明亮的青蓝色)
    lower_blue = np.array([80, 100, 100])
    upper_blue = np.array([120, 255, 255])
    mask_blue = cv2.inRange(hsv, lower_blue, upper_blue)

    # [关键步骤] 形态学膨胀：把蓝色的斜条纹“粘”在一起变成实心块
    kernel = np.ones((5, 5), np.uint8) # 5x5 的卷积核
    mask_blue = cv2.dilate(mask_blue, kernel, iterations=2)
    mask_yellow = cv2.dilate(mask_yellow, kernel, iterations=2)

    # ==============================
    # 步骤 D: 判定逻辑
    # ==============================
    status = "MISS"
    
    print(mask_yellow[roi.shape[0]//2, cursor_x])
    if cursor_found:
        # 获取光标所在位置的 mask 值 (255 表示在区域内，0 表示不在)
        # 这里的逻辑是：如果光标的 x 坐标对应的 mask 是白色的，就说明撞上了
        
        print(mask_yellow.shape, height, width)
        # for i in range(0, height):
            # 检查黄色 (优先)
        if mask_yellow[roi.shape[0]//2, cursor_x] == 255:
            status = "PERFECT (Yellow)"
        # 检查蓝色
        elif mask_blue[roi.shape[0]//2, cursor_x] == 255:
            status = "GOOD (Blue)"
            
    # ==============================
    # 可视化结果
    # ==============================
    print(f"当前判定状态: {status}")
    
    # 显示处理后的掩膜 (调试用)
    cv2.imshow("Original ROI", roi)
    cv2.imshow("Blue Mask (Dilated)", mask_blue)
    cv2.imshow("Yellow Mask", mask_yellow)
    cv2.waitKey(0)
    cv2.destroyAllWindows()

# 使用说明：将你的截图保存为 qte_test.png 并运行
analyze_fishing_bar('qte_test.png')