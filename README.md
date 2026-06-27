# 棕色尘埃2的python钓鱼脚本

## 介绍

基于图像识别进行QTE操作，只点击黄色区域，简单的QTE操作没问题，例如QTE条上有一些遮挡物，把黄色区域覆盖了，就容易失败

## 使用步骤——源码运行

+ 测试环境：
+ Python 3.12.4
+ Pypi 24.0

### 1. 创建虚拟环境

打开空文件夹，并在空文件夹打开`powershell`，输入下面命令

```sh
# py -版本 -m venv 环境名字
py -3.12 -m venv auto_fishing
```
### 2. 进入虚拟环境

继续输入下面命令进入虚拟环境

```sh
# .\环境名字\Scripts\activate
.\auto_fishing\Scripts\activate
```

### 3. 安装必要的依赖

```sh
pip install -r requirements.txt
```

### 4. 运行脚本

运行脚本后，点击一下游戏里，注意游戏界面要全部展示出来，**无其他窗口遮挡，窗口始终处于焦点状态**

```sh
python main.py
```

实际执行一次背包清理流程，不进入自动钓鱼循环：

```sh
python tools/clean_backpack_once.py
```

### 5. 运行测试

```sh
python -m unittest discover -s tests
```

## 使用步骤——exe运行

### 1. 下载压缩包

点击 [Release](https://github.com/hahg2000/auto_fishing/releases)；下载最新的版本里的压缩包制品

### 2. 双击运行

### 3. 然后切到游戏窗口

## 配置文件说明

程序从 `config.ini` 读取配置。下表中的“变量值”是仓库当前配置值，修改前建议保留一份可正常运行的配置。

- `*_percent` 使用 `0～100` 的百分比；`left/top/right/bottom` 分别表示区域的左、上、右、下边界。
- 背包点击坐标使用 `0～1` 的窗口比例，超出该范围可能点击到游戏窗口外。
- OpenCV HSV 中，Hue（色相）范围为 `0～180`，Saturation（饱和度）和 Value（明度）范围为 `0～255`。
- HSV 下限应小于或等于对应上限。颜色、坐标和像素阈值可能因分辨率、显示设置及游戏画面亮度而需要调整。

### `[hook]` 上钩检测

| 变量名 | 变量值 | 中文名 | 备注 |
| --- | ---: | --- | --- |
| `top_percent` | `25` | 感叹号区域上边界 | 相对游戏客户区 |
| `bottom_percent` | `36` | 感叹号区域下边界 | 相对游戏客户区 |
| `left_percent` | `49` | 感叹号区域左边界 | 相对游戏客户区 |
| `right_percent` | `51` | 感叹号区域右边界 | 相对游戏客户区 |
| `hook_lower_hue` | `20` | 上钩黄色色相下限 | 只用于感叹号黄色遮罩 |
| `hook_lower_saturation` | `35` | 上钩黄色饱和度下限 |  |
| `hook_lower_value` | `210` | 上钩黄色明度下限 |  |
| `hook_upper_hue` | `30` | 上钩黄色色相上限 |  |
| `hook_upper_saturation` | `120` | 上钩黄色饱和度上限 |  |
| `hook_upper_value` | `255` | 上钩黄色明度上限 |  |

### `[roi]` QTE 截图、颜色与挡板

| 变量名 | 变量值 | 中文名 | 备注 |
| --- | ---: | --- | --- |
| `top_percent` | `82` | QTE 整体区域上边界 | 相对游戏客户区 |
| `bottom_percent` | `90` | QTE 整体区域下边界 | 相对游戏客户区 |
| `left_percent` | `32` | QTE 整体区域左边界 | 相对游戏客户区 |
| `right_percent` | `65` | QTE 整体区域右边界 | 相对游戏客户区 |
| `time_top_percent` | `0` | 倒计时条上边界 | 相对 QTE 整体截图区域 |
| `time_bottom_percent` | `100` | 倒计时条下边界 | 相对 QTE 整体截图区域 |
| `time_left_percent` | `0` | 倒计时条左边界 | 相对 QTE 整体截图区域 |
| `time_right_percent` | `18` | 倒计时条右边界 | 相对 QTE 整体截图区域 |
| `qte_top_percent` | `50` | QTE 条上边界 | 相对 QTE 整体截图区域 |
| `qte_bottom_percent` | `97` | QTE 条下边界 | 相对 QTE 整体截图区域 |
| `qte_left_percent` | `22` | QTE 条左边界 | 相对 QTE 整体截图区域 |
| `qte_right_percent` | `100` | QTE 条右边界 | 相对 QTE 整体截图区域 |
| `qte_press_offset_pixels` | `0` | QTE 按键判定横向偏移 | 正数向右、负数向左；是否提前取决于光标移动方向，结果会限制在遮罩宽度内 |
| `time_lower_green_hue` | `65` | 倒计时绿色色相下限 |  |
| `time_lower_green_saturation` | `185` | 倒计时绿色饱和度下限 |  |
| `time_lower_green_value` | `210` | 倒计时绿色明度下限 |  |
| `time_upper_green_hue` | `75` | 倒计时绿色色相上限 |  |
| `time_upper_green_saturation` | `195` | 倒计时绿色饱和度上限 |  |
| `time_upper_green_value` | `255` | 倒计时绿色明度上限 |  |
| `time_lower_red_hue` | `170` | 倒计时红色色相下限 |  |
| `time_lower_red_saturation` | `155` | 倒计时红色饱和度下限 |  |
| `time_lower_red_value` | `240` | 倒计时红色明度下限 |  |
| `time_upper_red_hue` | `180` | 倒计时红色色相上限 |  |
| `time_upper_red_saturation` | `170` | 倒计时红色饱和度上限 |  |
| `time_upper_red_value` | `255` | 倒计时红色明度上限 |  |
| `yellow_lower_hue` | `20` | QTE 黄色色相下限 | 黄色区域按键判定 |
| `yellow_lower_saturation` | `125` | QTE 黄色饱和度下限 |  |
| `yellow_lower_value` | `220` | QTE 黄色明度下限 |  |
| `yellow_upper_hue` | `30` | QTE 黄色色相上限 |  |
| `yellow_upper_saturation` | `255` | QTE 黄色饱和度上限 |  |
| `yellow_upper_value` | `255` | QTE 黄色明度上限 |  |
| `red_lower_hue` | `170` | 破冰红色色相下限 | Frost 策略用于检测破冰提示 |
| `red_lower_saturation` | `100` | 破冰红色饱和度下限 |  |
| `red_lower_value` | `100` | 破冰红色明度下限 |  |
| `red_upper_hue` | `180` | 破冰红色色相上限 |  |
| `red_upper_saturation` | `255` | 破冰红色饱和度上限 |  |
| `red_upper_value` | `255` | 破冰红色明度上限 |  |
| `blue_lower_hue` | `95` | QTE 蓝色色相下限 | Abyss 策略在有效范围没有黄色时使用 |
| `blue_lower_saturation` | `105` | QTE 蓝色饱和度下限 |  |
| `blue_lower_value` | `255` | QTE 蓝色明度下限 |  |
| `blue_upper_hue` | `102` | QTE 蓝色色相上限 |  |
| `blue_upper_saturation` | `255` | QTE 蓝色饱和度上限 |  |
| `blue_upper_value` | `255` | QTE 蓝色明度上限 |  |
| `white_lower_hue` | `0` | 光标白色色相下限 | 用于定位 QTE 光标 |
| `white_lower_saturation` | `0` | 光标白色饱和度下限 | 饱和度范围过大会把挡板识别成光标 |
| `white_lower_value` | `240` | 光标白色明度下限 |  |
| `white_upper_hue` | `180` | 光标白色色相上限 | 白色低饱和时色相通常不稳定，因此覆盖完整色相范围 |
| `white_upper_saturation` | `10` | 光标白色饱和度上限 | 与挡板饱和度范围分离 |
| `white_upper_value` | `255` | 光标白色明度上限 |  |
| `blocker_one_lower_hue` | `0` | 挡板区间一色相下限 | 两组挡板 HSV 遮罩最终取并集 |
| `blocker_one_lower_saturation` | `25` | 挡板区间一饱和度下限 |  |
| `blocker_one_lower_value` | `230` | 挡板区间一明度下限 |  |
| `blocker_one_upper_hue` | `180` | 挡板区间一色相上限 |  |
| `blocker_one_upper_saturation` | `52` | 挡板区间一饱和度上限 |  |
| `blocker_one_upper_value` | `255` | 挡板区间一明度上限 |  |
| `blocker_two_lower_hue` | `0` | 挡板区间二色相下限 | 用于覆盖另一种亮度或透明状态 |
| `blocker_two_lower_saturation` | `0` | 挡板区间二饱和度下限 |  |
| `blocker_two_lower_value` | `200` | 挡板区间二明度下限 |  |
| `blocker_two_upper_hue` | `180` | 挡板区间二色相上限 |  |
| `blocker_two_upper_saturation` | `10` | 挡板区间二饱和度上限 | 需注意不要覆盖光标范围过多 |
| `blocker_two_upper_value` | `245` | 挡板区间二明度上限 |  |
| `blocker_shape_min_width` | `4` | 挡板轮廓最小宽度 | 参考分辨率下的像素值；实际按窗口宽度缩放，判断不包含等于下限的轮廓 |
| `blocker_shape_max_width` | `20` | 挡板轮廓最大宽度 | 参考分辨率下的像素值；实际按窗口宽度缩放，判断不包含等于上限的轮廓 |
| `blocker_shape_min_height` | `18` | 挡板轮廓最小高度 | 参考分辨率下的像素值；实际按窗口高度缩放，判断不包含等于下限的轮廓 |
| `blocker_shape_max_height` | `100` | 挡板轮廓最大高度 | 参考分辨率下的像素值；实际按窗口高度缩放，判断不包含等于上限的轮廓 |

### `[backpack]` 背包清理

| 变量名 | 变量值 | 中文名 | 备注 |
| --- | ---: | --- | --- |
| `button_click_interval_seconds` | `2` | 按钮点击间隔秒数 | 网络或动画较慢时可适当增大 |
| `one_click_sale_left` | `0.87` | 一键出售按钮横向位置 | 相对游戏客户区宽度的比例 |
| `one_click_sale_top` | `0.92` | 一键出售按钮纵向位置 | 相对游戏客户区高度的比例 |
| `select_all_left` | `0.82` | 全选按钮横向位置 | 相对游戏客户区宽度的比例 |
| `select_all_top` | `0.92` | 全选按钮纵向位置 | 相对游戏客户区高度的比例 |
| `circle_check_left` | `0.92` | 圆形确认按钮横向位置 | 相对游戏客户区宽度的比例 |
| `circle_check_top` | `0.92` | 圆形确认按钮纵向位置 | 相对游戏客户区高度的比例 |
| `dialog_confirm_left` | `0.57` | 提示框确定按钮横向位置 | 相对游戏客户区宽度的比例 |
| `dialog_confirm_top` | `0.61` | 提示框确定按钮纵向位置 | 相对游戏客户区高度的比例 |
| `quit_backpack_left` | `0.1` | 退出背包按钮横向位置 | 相对游戏客户区宽度的比例 |
| `quit_backpack_top` | `0.05` | 退出背包按钮纵向位置 | 相对游戏客户区高度的比例 |

### `[time]` 时间控制

| 变量名 | 变量值 | 中文名 | 备注 |
| --- | ---: | --- | --- |
| `round_end_wait_time` | `4` | 每轮结束等待秒数 | 网络或结算动画较慢时可增大 |
| `fish_end_wait_time` | `4` | 钓鱼成功后等待秒数 | 等待结束动画完成后再点击画面 |
| `begin_fish_wait_time` | `4` | 程序启动等待秒数 | 用于切换并聚焦游戏窗口 |
| `loop_sleep_seconds` | `0.02` | 检测循环休眠秒数 | 越小响应越快但 CPU 占用越高 |
| `longest_keep_time` | `35` | 单次 QTE 最长秒数 | 防止识别异常时永久卡在 QTE 循环 |

### `[scale]` 分辨率缩放

| 变量名 | 变量值 | 中文名 | 备注 |
| --- | ---: | --- | --- |
| `reference_window_width` | `1152` | 参考窗口宽度 | 像素数量阈值及挡板宽度以此分辨率为基准 |
| `reference_window_height` | `648` | 参考窗口高度 | 像素数量阈值及挡板高度以此分辨率为基准 |

### `[ocr]` OCR 识别

| 变量名 | 变量值 | 中文名 | 备注 |
| --- | ---: | --- | --- |
| `enabled` | `true` | OCR 总开关 | 关闭后不会自动识别地点或背包已满提示 |
| `debug_once_on_start` | `true` | 启动时 OCR 调试开关 | 当前代码会读取该值，但尚未执行对应的一次性调试流程 |
| `auto_select_strategy` | `true` | 自动选择 QTE 策略 | OCR 识别地点失败时回退到手动选择 |
| `change_location_on_missing_time` | `false` | 缺少“时”字时自动换点 | 默认关闭；OCR 波动可能导致误触发 |
| `location_left_percent` | `11` | 地点 OCR 区域左边界 | 相对游戏客户区 |
| `location_top_percent` | `8` | 地点 OCR 区域上边界 | 相对游戏客户区 |
| `location_right_percent` | `28` | 地点 OCR 区域右边界 | 相对游戏客户区 |
| `location_bottom_percent` | `15` | 地点 OCR 区域下边界 | 相对游戏客户区 |
| `backpack_full_left_percent` | `30` | 背包已满 OCR 区域左边界 | 相对游戏客户区 |
| `backpack_full_top_percent` | `20` | 背包已满 OCR 区域上边界 | 相对游戏客户区 |
| `backpack_full_right_percent` | `65` | 背包已满 OCR 区域右边界 | 相对游戏客户区 |
| `backpack_full_bottom_percent` | `30` | 背包已满 OCR 区域下边界 | 相对游戏客户区 |
| `use_cls` | `false` | OCR 文字方向分类 | 开启会增加处理步骤；普通横向中文通常无需开启 |
| `det_model_path` | 空 | OCR 检测模型路径 | 留空使用 RapidOCR 内置模型；自定义路径建议放在项目目录内以便打包 |
| `cls_model_path` | 空 | OCR 方向分类模型路径 | `use_cls=false` 时通常无需设置 |
| `rec_model_path` | 空 | OCR 文字识别模型路径 | 留空使用 RapidOCR 内置模型 |
| `rec_keys_path` | 空 | OCR 字符字典路径 | 自定义识别模型时应使用与模型匹配的字典 |

## 可能遇到的问题

- [x] 识别不到鱼上钩了（识别感叹号来判断鱼是否上钩，深渊巨口地图没有感叹号的匹配度会莫名得高——已判断黄色像素数量
- [x] 背包满了（功能完成了，需要多次测试
- [x] 对于一些干扰QTE的操作容易失败（因为出现的概率少所以不太好测试
- [x] 不同分辨率和颜色范围没有测试过（懂代码的可以自行调整代码里的颜色范围
- [x] 冰霜海峡的锁定光标需要连续点击空格的没有实现
- [ ] 不同分辨率和颜色范围提取到了配置文件，暂时方案：提交测试的工具，可自行修改；最终方案：按照游戏分辨率和颜色范围自动生成配置文件（限于设备因素应该是实现不了了）
- [x] 深渊巨口地图黄色部分有时会消失（增加黄色部分判定时间还是增加判定蓝色部分？
- [x] 深渊巨口地图出现多个光标（增加对比度来判断真的光标？
- [ ] 背包清理中途点击失误的处理：暂时重新再运行一遍背包清理操作，后面检测清理背包的每个阶段再进行操作

## 开发计划

地图：没有实现的默认用寒霜海峡钓鱼策略

+ 烟波湖：
+ 浅岸：
+ 寒霜海峡：
  + [x] 光标冰冻——判断qte条是否有红色像素
  + [x] 贝壳挡住光标——只要露出黄色部分都可以判断到
  + [x] 光标隐形——疯狂点击空格（光标隐藏后，黄色部分上下有会有点发光部分，就会疯狂按空格，歪打正着了
+ 深渊巨口：
  + [x] 多个光标出现——把真实光标颜色的范围缩小
  + [ ] 黄色部分消失，只有绿色部分
  + [x] 黄色部分消失，只要蓝色部分——当黄色部分检测不到时，开始检测蓝色部分
  + [ ] 产生有红色数字的泡泡（不知道有什么阻碍
  + [x] 产生隔板来反弹光标行动——不影响所以不处理

- [x] 引入ocr来判断当前钓鱼地点，来执行不同的钓鱼策略。（如果引入ocr，打包体积会增大。好处是自动识别钓鱼策略和不用触发三次突发时间才清理背包

## 开发指南

如果想自己开发新的地图钓鱼策略：

1. 在 `qte_strategy.py` 里继承 `BaseQTEStrategy` 类，在 `__init__` 初始化需要使用的变量，然后实现 `play_qte` 方法

2. 在 `main.py` 里的 `QTE_STRATEGIES_MAP` 增加刚新增的策略类

## 所使用的开源库

+ [mss](https://github.com/BoboTiG/python-mss/issues) —— —— 窗口截图
+ [dxcam](https://github.com/ra1nty/DXcam) —— 窗口截图
+ [opencv](https://github.com/opencv/opencv) —— 图像操作
+ [onnxruntime](https://github.com/microsoft/onnxruntime)
+ [rapidocr]() —— OCR支持
+ [pydirectinput](https://github.com/learncodebygaming/pydirectinput) —— 模拟操作
+ [pywin32](https://github.com/mhammond/pywin32) —— Windows API
+ [numpy](https://github.com/numpy/numpy)
