import win32gui
import configparser
import os
import sys

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
    
    # 3. 打印一下路径，方便调试（看到打包后它到底去哪里找文件了）
    print(f"正在读取配置文件路径: {full_path}") 
    config = configparser.ConfigParser()
    
    # 4. 使用拼接好的 full_path 进行判断和读取
    if not os.path.exists(full_path):
        # 这里建议把 full_path 打印出来，这样报错时你知道程序去哪个路径找文件失败了
        raise FileNotFoundError(f"配置文件未找到: {full_path}")
        
    config.read(full_path, encoding="utf-8")
    return config
