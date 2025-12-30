import win32gui
import mss
import cv2
import numpy as np
import ctypes
ctypes.windll.user32.SetProcessDPIAware()

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

# === 使用示例 ===
# 假设你的游戏标题栏显示的是 "Genshin Impact" 或者 "FishingGame"
# 请务必修改为你实际的游戏标题！
GAME_TITLE = "BrownDust II" 

def main_capture_loop():
  region = get_window_region(GAME_TITLE)
  if not region: return

  with mss.mss() as sct:
      while True:
          # 这里的 img 截取的仅仅是游戏窗口的内容
          img = np.array(sct.grab(region))
          
          # 显示出来看看对不对 (按q退出)
          cv2.imshow('Game Window Only', img)
          if cv2.waitKey(1) & 0xFF == ord('q'):
              break
  cv2.destroyAllWindows()