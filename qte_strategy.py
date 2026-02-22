import time
import cv2
import numpy as np
import pydirectinput
import utils

class BaseQTEStrategy:
    def __init__(self, config, region):
        self.longest_keep_time = utils.readConfigAndCastInt(config, "time", "longest_keep_time")
        self.fish_end_wait_time = float(config["time"]["fish_end_wait_time"])
        
        lower_white_hue = utils.readConfigAndCastInt(config, 'roi', 'lower_white_hue')
        lower_white_saturation = utils.readConfigAndCastInt(config, 'roi', 'lower_white_saturation')
        lower_white_value = utils.readConfigAndCastInt(config, 'roi', 'lower_white_value')
        upper_white_hue = utils.readConfigAndCastInt(config, 'roi', 'upper_white_hue')
        upper_white_saturation = utils.readConfigAndCastInt(config, 'roi', 'upper_white_saturation')
        upper_white_value = utils.readConfigAndCastInt(config, 'roi', 'upper_white_value')
        self.lower_white = np.array([lower_white_hue, lower_white_saturation, lower_white_value]) 
        self.upper_white = np.array([upper_white_hue, upper_white_saturation, upper_white_value])

        lower_yellow_hue = utils.readConfigAndCastInt(config, "roi", "lower_yellow_hue")
        lower_yellow_saturation = utils.readConfigAndCastInt(config, "roi", "lower_yellow_saturation")
        lower_yellow_value = utils.readConfigAndCastInt(config, "roi", "lower_yellow_value")
        upper_yellow_hue = utils.readConfigAndCastInt(config, "roi", "upper_yellow_hue")
        upper_yellow_saturation = utils.readConfigAndCastInt(config, "roi", "upper_yellow_saturation")
        upper_yellow_value = utils.readConfigAndCastInt(config, "roi", "upper_yellow_value")
        self.lower_yellow = np.array([lower_yellow_hue, lower_yellow_saturation, lower_yellow_value])
        self.upper_yellow = np.array([upper_yellow_hue, upper_yellow_saturation, upper_yellow_value])
        
        time_lower_green_hue = utils.readConfigAndCastInt(config, 'roi', 'time_lower_green_hue')
        time_lower_green_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_lower_green_saturation')
        time_lower_green_value = utils.readConfigAndCastInt(config, 'roi', 'time_lower_green_value')
        time_upper_green_hue = utils.readConfigAndCastInt(config, 'roi', 'time_upper_green_hue')
        time_upper_green_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_upper_green_saturation')
        time_upper_green_value = utils.readConfigAndCastInt(config, 'roi', 'time_upper_green_value')
        self.time_lower_green = np.array([time_lower_green_hue, time_lower_green_saturation, time_lower_green_value])
        self.time_upper_green = np.array([time_upper_green_hue, time_upper_green_saturation, time_upper_green_value])

        time_lower_red_hue = utils.readConfigAndCastInt(config, 'roi', 'time_lower_red_hue')
        time_lower_red_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_lower_red_saturation')
        time_lower_red_value = utils.readConfigAndCastInt(config, 'roi', 'time_lower_red_value')
        time_upper_red_hue = utils.readConfigAndCastInt(config, 'roi', 'time_upper_red_hue')
        time_upper_red_saturation = utils.readConfigAndCastInt(config, 'roi', 'time_upper_red_saturation')
        time_upper_red_value = utils.readConfigAndCastInt(config, 'roi', 'time_upper_red_value')
        self.time_lower_red = np.array([time_lower_red_hue, time_lower_red_saturation, time_lower_red_value])
        self.time_upper_red = np.array([time_upper_red_hue, time_upper_red_saturation, time_upper_red_value])

        roi_top_percent = utils.readConfigAndCastInt(config, "roi", "top_percent")
        roi_bottom_percent = utils.readConfigAndCastInt(config, "roi", "bottom_percent")
        roi_left_percent = utils.readConfigAndCastInt(config, "roi", "left_percent")
        roi_right_percent = utils.readConfigAndCastInt(config, "roi", "right_percent")
        
        time_top_percent = utils.readConfigAndCastInt(config, 'roi', 'time_top_percent')
        time_bottom_percent = utils.readConfigAndCastInt(config, 'roi', 'time_bottom_percent')
        time_left_percent = utils.readConfigAndCastInt(config, 'roi', 'time_left_percent')
        time_right_percent = utils.readConfigAndCastInt(config, 'roi', 'time_right_percent')

        self.roi_pos = {
            "left": region["left"] + int(region["width"] * roi_left_percent / 100),
            "top": region["top"] + int(region["height"] * roi_top_percent / 100),
            "width": int(region["width"] * (roi_right_percent - roi_left_percent) / 100),
            "height": int(region["height"] * (roi_bottom_percent - roi_top_percent) / 100)
        }

        self.rot_pos = {
            "left": region["left"] + int(region["width"] * time_left_percent / 100),
            "top": region["top"] + int(region["height"] * time_top_percent / 100),
            "width": int(region["width"] * (time_right_percent - time_left_percent) / 100),
            "height": int(region["height"] * (time_bottom_percent - time_top_percent) / 100)
        }
    def play_qte(self, sct, region):
        """核心执行方法，子类必须重写这个方法"""
        raise NotImplementedError("子类必须实现 play_qte() 方法")
    
    def finish_fishing(self, window_center_x, window_center_y):
        # 移动鼠标到窗口中心 (防止点歪)
        pydirectinput.moveTo(window_center_x, window_center_y)
        time.sleep(0.2)
        # 点击左键
        pydirectinput.click()
    
class FrostStraitQTEStrategy(BaseQTEStrategy):
    """默认钓鱼点：只看黄色条"""
    def __init__(self, config, region):
        super().__init__(config, region)
        lower_red_hue = utils.readConfigAndCastInt(config, "roi", "lower_red_hue")
        lower_red_saturation = utils.readConfigAndCastInt(config, "roi", "lower_red_saturation")
        lower_red_value = utils.readConfigAndCastInt(config, "roi", "lower_red_value")
        upper_red_hue = utils.readConfigAndCastInt(config, "roi", "upper_red_hue")
        upper_red_saturation = utils.readConfigAndCastInt(config, "roi", "upper_red_saturation")
        upper_red_value = utils.readConfigAndCastInt(config, "roi", "upper_red_value")
        self.lower_red = np.array([lower_red_hue, lower_red_saturation, lower_red_value])
        self.upper_red = np.array([upper_red_hue, upper_red_saturation, upper_red_value])

    def play_qte(self, sct, region):
        print(">>> 开始 QTE...")

        no_bar_frames = 0
        start_time = time.time()
        while time.time() - start_time < self.longest_keep_time:
            # 提取qte条的范围
            roi = np.array(sct.grab(self.roi_pos))
            rot = np.array(sct.grab(self.rot_pos))
            
            # MSS 默认是 BGRA
            roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR) 
            roi_hsv = cv2.cvtColor(roi_hsv, cv2.COLOR_BGR2HSV)
            rot_hsv = cv2.cvtColor(rot, cv2.COLOR_BGRA2BGR)
            rot_hsv = cv2.cvtColor(rot_hsv, cv2.COLOR_BGR2HSV)
            
            # 提取黄色区域
            mask_yellow = utils.create_color_mask(self.lower_yellow, self.upper_yellow, roi_hsv)
            
            # 提取时间条的绿色和红色区域
            mask_green_time = utils.create_color_mask(self.time_lower_green, self.time_upper_green, rot_hsv, is_dilate=False)
            mask_red_time = utils.create_color_mask(self.time_lower_red, self.time_upper_red, rot_hsv, is_dilate=False)
            time_red_pixel_count = cv2.countNonZero(mask_red_time) * 20
            time_green_pixel_count = cv2.countNonZero(mask_green_time) * 10
            
            # 防止有其他有元素干扰
            if time_red_pixel_count + time_green_pixel_count > 1000: 
                no_bar_frames = 0
                # 找到光标位置
                mask_cursor = utils.create_color_mask(self.lower_white, self.upper_white, roi_hsv, is_dilate=False)
                col_sums = np.sum(mask_cursor, axis=0)
                # 找到白色像素最多的那一列的索引
                cursor_x = np.argmax(col_sums)
                
                if (self.solve_ice_trouble(roi_hsv)):
                    continue
                
                # 如果画面里没有白色，cursor_x 可能是 0，需要防呆
                if np.max(col_sums) > 0: 
                    check_y = roi.shape[0] // 2
                    if mask_yellow[check_y, cursor_x]:
                        print(">>> 击中了黄色区域")
                        pydirectinput.press("space")     
                
            else:
                no_bar_frames += 1

                if no_bar_frames > 30:
                    print(">>> 钓鱼结束")
                    # 等待鱼结束动画
                    time.sleep(self.fish_end_wait_time)
                    self.finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                    break  
                        
    def solve_ice_trouble(self, roi_hsv):
        """
        检测并解决冰冻状态
        :param roi_hsv: 当前QTE画面的 HSV 数据
        :return: True 如果检测到冰冻并执行了操作，False 如果无冰冻
        """
        mask = cv2.inRange(roi_hsv, self.lower_red, self.upper_red) 
        
        # 计算红色像素数量，阈值设为 10 左右
        if cv2.countNonZero(mask) > 5: 
            print(">>> 检测到冰冻！正在破冰 (按空格)...")
            pydirectinput.press('space')
            # 为了防止按太快游戏不识别，给个极短的间隔
            time.sleep(0.05) 
            return True
        
        return False
    
class AbyssMawQTEStrategy(BaseQTEStrategy):
    def __init__(self, config, region):
        super().__init__(config, region)
        lower_blue_hue = utils.readConfigAndCastInt(config, "roi", "lower_blue_hue")
        lower_blue_saturation = utils.readConfigAndCastInt(config, "roi", "lower_blue_saturation")
        lower_blue_value = utils.readConfigAndCastInt(config, "roi", "lower_blue_value")
        upper_blue_hue = utils.readConfigAndCastInt(config, "roi", "upper_blue_hue")
        upper_blue_saturation = utils.readConfigAndCastInt(config, "roi", "upper_blue_saturation")
        upper_blue_value = utils.readConfigAndCastInt(config, "roi", "upper_blue_value")
        self.lower_blue = np.array([lower_blue_hue, lower_blue_saturation, lower_blue_value])
        self.upper_blue = np.array([upper_blue_hue, upper_blue_saturation, upper_blue_value])

    def play_qte(self, sct, region):
        print(">>> 开始 QTE...")

        no_bar_frames = 0
        start_time = time.time()
        while time.time() - start_time < self.longest_keep_time:
            # 提取qte条的范围
            roi = np.array(sct.grab(self.roi_pos))
            rot = np.array(sct.grab(self.rot_pos))
            
            # MSS 默认是 BGRA
            roi_hsv = cv2.cvtColor(roi, cv2.COLOR_BGRA2BGR) 
            roi_hsv = cv2.cvtColor(roi_hsv, cv2.COLOR_BGR2HSV)
            rot_hsv = cv2.cvtColor(rot, cv2.COLOR_BGRA2BGR)
            rot_hsv = cv2.cvtColor(rot_hsv, cv2.COLOR_BGR2HSV)
            
            # 提取黄色区域
            mask_yellow = utils.create_color_mask(self.lower_yellow, self.upper_yellow, roi_hsv)
            mask_blue = utils.create_color_mask(self.lower_blue, self.upper_blue, roi_hsv)
            
            # 提取时间条的绿色和红色区域
            mask_green_time = utils.create_color_mask(self.time_lower_green, self.time_upper_green, rot_hsv, is_dilate=False)
            mask_red_time = utils.create_color_mask(self.time_lower_red, self.time_upper_red, rot_hsv, is_dilate=False)
            time_red_pixel_count = cv2.countNonZero(mask_red_time) * 20
            time_green_pixel_count = cv2.countNonZero(mask_green_time) * 10
            
            # 防止有其他有元素干扰
            if time_red_pixel_count + time_green_pixel_count > 1000: 
                no_bar_frames = 0
                # 找到光标位置
                mask_cursor = utils.create_color_mask(self.lower_white, self.upper_white, roi_hsv, is_dilate=False)
                col_sums = np.sum(mask_cursor, axis=0)
                # 找到白色像素最多的那一列的索引
                cursor_x = np.argmax(col_sums)
                
                # 如果画面里没有白色，cursor_x 可能是 0，需要防呆
                if np.max(col_sums) > 0: 
                    check_y = roi.shape[0] // 2
                    
                    mask_yellow_pixel_count = cv2.countNonZero(mask_yellow)
                    
                    if mask_yellow_pixel_count > 300:
                        if mask_yellow[check_y, cursor_x]:
                            print(">>> 击中了黄色区域")
                            pydirectinput.press("space")
                    else:
                        if mask_blue[check_y, cursor_x]:
                            print(">>> 击中了蓝色区域")
                            pydirectinput.press("space")
                
            else:
                no_bar_frames += 1

                if no_bar_frames > 30:
                    print(">>> 钓鱼结束")
                    # 等待鱼结束动画
                    time.sleep(self.fish_end_wait_time)
                    self.finish_fishing(region["left"] + region["width"]//2, region["top"] + region["height"]//2)
                    break