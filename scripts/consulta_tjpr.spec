# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['smoke_test_pje.py'],
    pathex=['D:\\Autonomus'],
    binaries=[],
    datas=[],
    hiddenimports=[
        'playwright.async_api',
        'playwright.sync_api',
        'loguru',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'torch',
        'torchvision',
        'torchaudio',
        'transformers',
        'scipy',
        'sklearn',
        'pandas',
        'tensorflow',
        'onnxruntime',
        'pyarrow',
        'faiss',
        'cv2',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher_advance=False,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher_advance=False)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='consulta_tjpr',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
