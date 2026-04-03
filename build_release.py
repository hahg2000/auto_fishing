from __future__ import annotations

import argparse
import configparser
import importlib.metadata
import os
import re
import subprocess
import sys
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

APP_NAME = "BD2_AutoFishing"
PROJECT_ROOT = Path(__file__).resolve().parent
DIST_DIR = PROJECT_ROOT / "dist"
CONFIG_PATH = PROJECT_ROOT / "config.ini"
MODEL_PATH_KEYS = (
    "det_model_path",
    "cls_model_path",
    "rec_model_path",
    "rec_keys_path",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a release package for BD2_AutoFishing with bundled OCR assets.",
    )
    parser.add_argument(
        "--nvidia",
        action="store_true",
        help="Include NVIDIA CUDA and cuDNN related binaries.",
    )
    return parser.parse_args()


def requirement_name(requirement: str) -> str:
    return re.split(r"[ ;(<>=\\[]", requirement, maxsplit=1)[0].strip()


def has_distribution(package_name: str) -> bool:
    try:
        importlib.metadata.distribution(package_name)
    except importlib.metadata.PackageNotFoundError:
        return False
    return True


def gather_copy_metadata_targets() -> list[str]:
    targets: set[str] = set()
    for package_name in ("rapidocr", "onnxruntime"):
        if has_distribution(package_name):
            targets.add(package_name)

        try:
            metadata = importlib.metadata.metadata(package_name)
        except importlib.metadata.PackageNotFoundError:
            continue

        for requirement in metadata.get_all("Requires-Dist") or []:
            name = requirement_name(requirement)
            if name and has_distribution(name):
                targets.add(name)

    return sorted(targets)


def resolve_configured_path(config_value: str) -> Path:
    raw_path = Path(config_value)
    if raw_path.is_absolute():
        return raw_path
    return (PROJECT_ROOT / raw_path).resolve()


def validate_project_file(path: Path) -> Path:
    if not path.is_file():
        raise FileNotFoundError(str(path))

    try:
        path.relative_to(PROJECT_ROOT)
    except ValueError as exc:
        raise ValueError(str(path)) from exc

    return path


def load_model_files() -> list[Path]:
    if not CONFIG_PATH.exists():
        raise SystemExit(f"config.ini not found: {CONFIG_PATH}")

    config = configparser.ConfigParser()
    config.read(CONFIG_PATH, encoding="utf-8-sig")

    model_files: list[Path] = []
    missing_files: list[Path] = []
    external_files: list[Path] = []

    for key in MODEL_PATH_KEYS:
        config_value = config.get("ocr", key, fallback="").strip()
        if not config_value:
            continue

        resolved_path = resolve_configured_path(config_value)
        try:
            validated_path = validate_project_file(resolved_path)
        except FileNotFoundError:
            missing_files.append(resolved_path)
            continue
        except ValueError:
            external_files.append(resolved_path)
            continue

        model_files.append(validated_path)

    if missing_files:
        joined = "\n".join(f"  - {path}" for path in missing_files)
        raise SystemExit(
            "Configured OCR model file not found. "
            "Make sure these ONNX/dictionary files exist first:\n"
            f"{joined}"
        )

    if external_files:
        joined = "\n".join(f"  - {path}" for path in external_files)
        raise SystemExit(
            "OCR model files must be stored inside the project folder "
            "for a portable release build. Move them into the repo first:\n"
            f"{joined}"
        )

    return model_files


def add_data_args(cmd: list[str], source_path: Path, destination_root: str) -> None:
    cmd.extend(["--add-data", f"{source_path}{os.pathsep}{destination_root}"])


def build_pyinstaller_command(*, include_nvidia: bool, model_files: list[Path]) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "PyInstaller",
        "main.py",
        "--noconfirm",
        "--clean",
        "--onedir",
        "--name",
        APP_NAME,
        "--console",
        "--collect-data",
        "rapidocr",
        "--collect-submodules",
        "rapidocr",
        "--collect-binaries",
        "onnxruntime",
    ]

    cmd.extend([
        "--exclude-module", "tkinter",
        "--exclude-module", "matplotlib",
        "--exclude-module", "PyQt5",
        "--exclude-module", "PySide6",
        "--exclude-module", "IPython",
        "--exclude-module", "pandas",
    ])


    if include_nvidia:
        cmd.extend(["--collect-binaries", "nvidia"])

    for package_name in gather_copy_metadata_targets():
        cmd.extend(["--copy-metadata", package_name])

    add_data_args(cmd, CONFIG_PATH, ".")

    seen_files: set[Path] = set()
    for model_file in model_files:
        if model_file in seen_files:
            continue
        seen_files.add(model_file)
        relative_parent = model_file.relative_to(PROJECT_ROOT).parent.as_posix()
        add_data_args(cmd, model_file, relative_parent)

    return cmd


def zip_dist_folder(package_dir: Path) -> Path:
    zip_path = DIST_DIR / f"{APP_NAME}-windows.zip"
    if zip_path.exists():
        zip_path.unlink()

    with ZipFile(zip_path, "w", compression=ZIP_DEFLATED) as archive:
        for file_path in sorted(path for path in package_dir.rglob("*") if path.is_file()):
            archive_name = Path(APP_NAME) / file_path.relative_to(package_dir)
            archive.write(file_path, arcname=archive_name.as_posix())

    return zip_path


def main() -> None:
    args = parse_args()

    try:
        import rapidocr  # noqa: F401
        import onnxruntime  # noqa: F401
    except ImportError as exc:
        raise SystemExit(
            "RapidOCR or ONNXRuntime is not available in the current environment. "
            "Install the OCR dependencies first."
        ) from exc

    model_files = load_model_files()
    command = build_pyinstaller_command(include_nvidia=args.nvidia, model_files=model_files)

    print("Running PyInstaller command:")
    print(" ".join(str(part) for part in command))
    subprocess.run(command, check=True, cwd=PROJECT_ROOT)

    package_dir = DIST_DIR / APP_NAME
    if not package_dir.is_dir():
        raise SystemExit(f"PyInstaller output directory not found: {package_dir}")

    zip_path = zip_dist_folder(package_dir)
    print(f">>> Build output directory: {package_dir}")
    print(f">>> Release zip: {zip_path}")


if __name__ == "__main__":
    main()
