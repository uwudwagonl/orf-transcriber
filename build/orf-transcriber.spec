# PyInstaller spec — produces a one-folder Windows build under build/dist/
# Run from the project root via:
#   pyinstaller build/orf-transcriber.spec --noconfirm
#
# The spec bundles binaries that have already been fetched into build/vendor/.
# See build/scripts/fetch-deps.ps1 for how those get there.
# ruff: noqa
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

PROJECT_ROOT = Path(SPECPATH).resolve().parent
VENDOR = PROJECT_ROOT / "build" / "vendor"
ASSETS = PROJECT_ROOT / "assets"

# ── Hidden imports ─────────────────────────────────────────────────────────
hiddenimports = []
hiddenimports += collect_submodules("faster_whisper")
hiddenimports += collect_submodules("ctranslate2")
hiddenimports += collect_submodules("tokenizers")
hiddenimports += collect_submodules("huggingface_hub")
hiddenimports += [
    "onnxruntime",
    "onnxruntime.capi._pybind_state",
    "av",  # used by faster-whisper for some inputs
]

# ── Data files (model configs, tokenizer assets shipped inside packages) ──
datas = []
datas += collect_data_files("faster_whisper")
datas += collect_data_files("ctranslate2")
datas += collect_data_files("tokenizers")
datas += collect_data_files("huggingface_hub")

# ── Bundled native binaries (placed alongside the exe in a `bin/` folder) ─
binaries = []
for name in ("orfondl.exe", "ffmpeg.exe", "ffprobe.exe"):
    src = VENDOR / name
    if src.exists():
        # second tuple element is destination directory inside the bundle
        binaries.append((str(src), "bin"))


block_cipher = None


a = Analysis(
    [str(PROJECT_ROOT / "build" / "launcher.py")],
    pathex=[str(PROJECT_ROOT / "src")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=[
        "matplotlib",
        "scipy",
        "pandas",
        "PIL",
        "IPython",
        "tornado",
        "notebook",
    ],
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

icon_path = ASSETS / "icon.ico"

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="OrfTranscriber",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,            # no console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path) if icon_path.exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="OrfTranscriber",
)
