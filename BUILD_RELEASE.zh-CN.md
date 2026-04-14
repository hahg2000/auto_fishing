# 构建与发布

## 1. 准备 OCR 模型文件

默认情况下，项目使用 `rapidocr` Python 包内置打包的模型。

如果你想使用内置模型，请在 `config.ini` 中保持以下键为空：

- `det_model_path`
- `cls_model_path`
- `rec_model_path`
- `rec_keys_path`

如果你之后想切换为自己准备的、兼容 RapidOCR 的 ONNX 模型，请在 `[ocr]` 段中填写这些路径。

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

推送提交后，创建并发布一个 GitHub Release。

注意：

- GitHub Actions 会自动打包 `rapidocr` 的内置模型数据
- 如果你之后切换回自己本地的模型文件，这些文件也必须存在于仓库检出内容中

工作流会自动执行以下步骤：

- 安装 RapidOCR、ONNXRuntime 和 PyInstaller
- 运行 `python build_release.py`
- 上传 `dist/BD2_AutoFishing-windows.zip`
- 将该 zip 附加到 GitHub Release
