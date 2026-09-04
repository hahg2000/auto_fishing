# 构建与发布

## 1. 准备 OCR 模型文件

默认情况下，项目使用 `rapidocr` Python 包内置打包的模型。

如果你想使用内置模型，请在 `config.ini` 中保持以下键为空：

- `det_model_path`
- `cls_model_path`
- `rec_model_path`
- `rec_keys_path`

如果你之后想切换为自己准备的、兼容 RapidOCR 的 ONNX 模型，请在 `[ocr]` 段中填写这些路径。

注意：自定义模型文件必须放在项目目录内（不能使用项目外的绝对路径），否则构建脚本会报错中止，以保证发布包在其他机器上也能正常使用。

## 2. 安装构建环境

安装构建环境：

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## 3. 本地构建

```powershell
python build_release.py
```

如果你需要打包包含 NVIDIA 相关二进制的 GPU 版本：

```powershell
python build_release.py --nvidia
```

本地产物如下：

- `dist/BD2_AutoFishing/`
- `dist/BD2_AutoFishing-windows.zip`

PyInstaller 完成后，构建脚本会自动删除 OpenCV 的 FFmpeg 视频 DLL，因为本项目没有使用
`cv2.VideoCapture` 或 `cv2.VideoWriter`。如果以后增加视频输入或输出功能，需要先移除该清理步骤。

## 4. 本地测试

运行：

```powershell
.\dist\BD2_AutoFishing\BD2_AutoFishing.exe
```

请确认：

- OCR 日志输出正常
- 打包后的程序能够正确找到 `config.ini`
- 打包后的程序能够正常初始化 RapidOCR 内置模型

## 5. 发布到 GitHub

推送提交后，创建并发布一个 GitHub Release（工作流在 Release 发布时自动触发）。也可以不发布 Release，直接在 GitHub 的 Actions 页面手动触发该工作流。

注意：

- GitHub Actions 会自动打包 `rapidocr` 的内置模型数据
- 如果你之后切换回自己本地的模型文件，这些文件也必须存在于仓库检出内容中

工作流（`.github/workflows/build.yml`）在 Windows + Python 3.12.4 环境下自动执行以下步骤：

- 安装 `requirements.txt` 中的依赖和 PyInstaller
- 运行 `python build_release.py`
- 上传 `dist/BD2_AutoFishing-windows.zip` 作为构建产物
- 发布 Release 时将该 zip 附加到 Release
