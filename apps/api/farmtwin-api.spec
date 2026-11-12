# PyInstaller spec for the desktop backend (ADR-022): one folder, started by the Tauri shell.
#   uv run pyinstaller farmtwin-api.spec --noconfirm   ->  dist/farmtwin-api/
from pathlib import Path

import sqlite_vec
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

datas = [
    ("alembic.ini", "."),
    ("migrations", "migrations"),
    ("../../knowledge", "knowledge"),
    ("app/ai/prompts", "app/ai/prompts"),
]
datas += collect_data_files("fastembed")
# sqlite-vec's loadable extension (vec0.so / .dylib / .dll) sits next to its __init__.py and
# isn't picked up as a library, so it's listed by hand
binaries = [(str(p), "sqlite_vec") for p in Path(sqlite_vec.__file__).parent.glob("vec0.*")]

a = Analysis(
    ["app/serve.py"],
    pathex=["."],
    datas=datas,
    binaries=binaries,
    # uvicorn loads the app by name, and alembic imports migration files by path
    hiddenimports=collect_submodules("app") + collect_submodules("uvicorn") + ["alembic.runtime.migration"],
    # the PyTorch voice stack (ml extra) never ships in the desktop app
    excludes=["torch", "transformers", "soundfile", "tkinter", "matplotlib"],
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="farmtwin-api", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="farmtwin-api")
