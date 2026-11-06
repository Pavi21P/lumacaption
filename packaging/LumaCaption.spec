# Reproducible folder recipe; run through Build-Windows.ps1.
from pathlib import Path
import os

from PyInstaller.utils.hooks import collect_data_files, copy_metadata

root = Path(SPECPATH).parent
stage = Path(os.environ["LUMACAPTION_BUILD_STAGE"])
datas = [
    (str(stage / "lumacaption-0.1.0.dist-info"), "lumacaption-0.1.0.dist-info"),
    (str(root / "scripts" / "verify_offline.py"), "."),
]
# Transformers builds lazy import maps by reading source files.
datas += collect_data_files("transformers", include_py_files=True)
for package in ("Pillow", "torch", "transformers", "truststore"):
    datas += copy_metadata(package, recursive=True)
hiddenimports = [
    "transformers.models.blip.configuration_blip",
    "transformers.models.blip.processing_blip",
    "transformers.models.blip.image_processing_blip",
    "transformers.models.blip.modeling_blip",
    "transformers.models.blip.modeling_blip_text",
    "transformers.models.bert.tokenization_bert",
    "transformers.models.bert.tokenization_bert_fast",
    "transformers.generation.utils",
    "lumacaption.desktop", "lumacaption.diagnostics", "lumacaption.batch",
    "requests.sessions", "unittest.mock",
]
a = Analysis(
    [str(root / "packaging" / "entry.py")],
    pathex=[str(root / "src")], binaries=[], datas=datas,
    hiddenimports=hiddenimports, hookspath=[], runtime_hooks=[],
    excludes=["pytest", "_pytest", "ruff", "pip", "IPython", "matplotlib",
              "tensorflow", "flax", "jax", "onnx", "onnxruntime"],
    noarchive=False,
)
pyz = PYZ(a.pure)
gui = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LumaCaption",
          debug=False, strip=False, upx=False, console=False)
cli = EXE(pyz, a.scripts, [], exclude_binaries=True, name="LumaCaption-CLI",
          debug=False, strip=False, upx=False, console=True)
COLLECT(gui, cli, a.binaries, a.datas, strip=False, upx=False, name="LumaCaption")
