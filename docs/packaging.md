# Packaging

MiniCI will be distributed as a Python package and as platform-specific
PyInstaller artifacts. External Python entry-point plugins are supported by the
Python package distribution; standalone binaries only guarantee bundled plugins.

Build on each target operating system:

```powershell
python -m pip install -e ".[release]"
pyinstaller --clean --noconfirm packaging/minici.spec
```

PyInstaller does not cross-compile. Windows, Linux, and macOS artifacts must be
built on their respective platforms.
