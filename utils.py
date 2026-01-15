import win32gui
import configparser
import os
import sys

# 默认的配置内容
DEFAULT_CONFIG_CONTENT = """[hook]
; 感叹号位置
top_percent = 29
bottom_percent = 41
left_percent = 47
right_percent = 53

; 感叹号匹配度，游戏分辨率越大，感叹号的匹配度可能就越小
match_percent = 0.60

[roi]
; qte位置
top_percent = 85
bottom_percent = 89
left_percent = 39
right_percent = 65

; 黄色颜色区间
lower_yellow_hue = 20
lower_yellow_saturation = 100
lower_yellow_value = 185

upper_yellow_hue = 30
upper_yellow_saturation = 255
upper_yellow_value = 255

[backpack]
; 一键出售按钮位置
one_click_sale_left = 0.87
one_click_sale_top = 0.92

; 全选按钮位置
select_all_left = 0.82
select_all_top = 0.92

; 圆形打钩按钮位置
circle_check_left = 0.92
circle_check_top = 0.92

; 提示框确定按钮位置
dialog_confirm_left = 0.57
dialog_confirm_top = 0.61

; 退出背包位置
quit_backpack_left = 0.1
quit_backpack_top = 0.12

[time]
; 一轮钓鱼结束后等待的时间，根据网络情况可以调整
round_end_wait_time = 2

; 钓鱼成功后的停留时间，来等待动画效果结束，根据电脑情况可以调整
fish_end_wait_time = 3

; 执行脚本后的停留时间，来预留时间能切换到游戏界面
begin_fish_wait_time = 3
"""

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

def get_resource_path(relative_path):
    """
    获取资源文件的绝对路径。
    用于访问打包进 exe 内部的图片资源。
    """
    if hasattr(sys, '_MEIPASS'):
        # PyInstaller 会把资源解压到 sys._MEIPASS 临时目录下
        return os.path.join(sys._MEIPASS, relative_path)
    
    # 普通运行模式，直接返回当前目录下的文件
    return os.path.join(os.path.abspath("."), relative_path)

def read_ini(filename: str = "config.ini"):
    """
    从ini文件读取配置文件，自动适配 .py 脚本运行和 .exe 打包运行环境
    :param filename: 文件名 (例如 "config.ini")
    :return: config对象
    """
    # 1. 获取当前程序的基础路径
    if getattr(sys, 'frozen', False):
        # 如果是打包后的 .exe 运行，获取 .exe 所在的目录
        base_path = os.path.dirname(sys.executable)
    else:
        # 如果是 .py 脚本运行，获取当前脚本所在的目录
        base_path = os.path.dirname(os.path.abspath(__file__))

    # 2. 将基础路径和文件名拼接成【绝对路径】
    full_path = os.path.join(base_path, filename)
    
    print(f">>> 正在读取配置文件路径: {full_path}") 
    config = configparser.ConfigParser()
    
    if not os.path.exists(full_path):
        print(f">>> 配置文件未找到，正在生成默认配置: {full_path}")
        try:
            with open(full_path, 'w', encoding='utf-8-sig') as f:
                f.write(DEFAULT_CONFIG_CONTENT)
        except Exception as e:
            print(f">>> 无法写入配置文件: {e}")
        
    config.read(full_path, encoding="utf-8-sig")
    return config
