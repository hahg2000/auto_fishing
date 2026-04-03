# Build And Release

## 1. Prepare OCR model files

By default the project uses the builtin models packaged inside the `rapidocr`
Python package.

In `config.ini`, leave these keys blank to use the builtin models:

- `det_model_path`
- `cls_model_path`
- `rec_model_path`
- `rec_keys_path`

If you want to switch to your own RapidOCR-compatible ONNX model set later,
fill these paths in `[ocr]`.

## 2. Install the build environment

Install the build environment:

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install pyinstaller
```

## 3. Build locally

```powershell
python build_release.py
```

If you need a GPU build that bundles NVIDIA related binaries:

```powershell
python build_release.py --nvidia
```

The local output will be:

- `dist/BD2_AutoFishing/`
- `dist/BD2_AutoFishing-windows.zip`

## 4. Test locally

Run:

```powershell
.\dist\BD2_AutoFishing\BD2_AutoFishing.exe
```

Check that:

- OCR logs appear normally.
- The packaged app can find `config.ini`.
- The packaged app can initialize RapidOCR builtin models normally.

## 5. Publish on GitHub

Push the commit, then create and publish a GitHub Release.

Important:

- GitHub Actions will package the builtin `rapidocr` model data automatically.
- If you later switch back to your own local model files, those files must also exist in the repository checkout.

The workflow will:

- install RapidOCR, ONNXRuntime, and PyInstaller
- run `python build_release.py`
- upload `dist/BD2_AutoFishing-windows.zip`
- attach the zip to the GitHub Release
