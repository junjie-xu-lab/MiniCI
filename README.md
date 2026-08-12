# MiniCI

MiniCI is a lightweight, local-first CI/CD runner for installation, testing,
building and other project tasks. It runs without an account, hosted server,
commercial API or AI service.

## Features

- Strict versioned YAML with validation and resolved dry runs.
- Sequential stages, parallel steps, retries, timeouts and conditions.
- Local commands plus an optional Docker CLI runner.
- SQLite history, redacted text logs and offline HTML reports.
- Git metadata, debounced file watching and overlapping-run protection.
- Local FastAPI dashboard and versioned Python entry-point plugin hooks.
- Windows, Linux and macOS source support; Windows standalone executable.

## Requirements

- Python 3.10 or newer for package installation.
- Git is optional and only used for metadata and branch/path conditions.
- Docker is optional and only required by Docker runner steps.

## Quick start

```powershell
python -m pip install .
minici init
minici validate --resolved
minici run --dry-run
minici run
minici status
minici dashboard
```

The standalone Windows executable does not require Python for MiniCI itself,
although configured commands can still require Python or other project tools.

## Configuration

`minici init` creates `minici.yml`. A minimal Python pipeline is:

```yaml
version: 1
project:
  name: example
stages:
  - name: quality
    steps:
      - name: test
        commands:
          - argv: [python, -m, pytest]
```

Use `argv` for portable direct execution and `run` when shell features are
needed. Full options are documented in
[`docs/configuration.md`](docs/configuration.md).

Input is `minici.yml`, project files and the selected environment. Output is
terminal status and a `.minici/` directory containing SQLite history, logs and
HTML reports.

## Commands

| Command | Purpose |
| --- | --- |
| `minici init` | Create a safe default configuration. |
| `minici validate --resolved` | Validate and show inherited settings. |
| `minici run [--dry-run]` | Plan or execute a pipeline. |
| `minici status` | Show recent runs. |
| `minici logs RUN_ID` | Print a run log. |
| `minici report RUN_ID` | Show a report path. |
| `minici watch` | Run after debounced file changes. |
| `minici dashboard` | Start the dashboard on `127.0.0.1`. |
| `minici doctor` | Check Git, Docker, storage and plugins. |
| `minici plugin-list` | List discovered plugins. |
| `minici version --verbose` | Show version and platform details. |

## Runtime layout

```text
.minici/
├── minici.db
├── run.lock
└── runs/<run-uid>/
    ├── run.log
    └── report.html
```

`.minici/` is ignored by Git. Logs are the complete output source; SQLite keeps
structured history and bounded command summaries.

## Docker and plugins

Docker steps use the local Docker CLI, do not request privileged mode and do not
mount the Docker socket. Python package installations discover plugins through
the `minici.plugins` entry-point group. Standalone binaries only guarantee
plugins bundled during their build.

## Security

`minici.yml` and plugins can execute code with your user permissions. Only run
trusted projects and plugins. Known secret environment values are redacted from
logs, but MiniCI is not a sandbox. The dashboard has no authentication and must
remain bound to localhost unless protected externally. See [SECURITY.md](SECURITY.md).

## Development and testing

On Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev,release]"
python -m pytest --cov=minici
ruff check .
ruff format --check .
python -m build
pyinstaller --clean --noconfirm packaging/minici.spec
```

PyInstaller must run separately on each target operating system. CI tests Python
3.10–3.12 on Windows, Ubuntu and macOS; the release workflow builds native
artifacts.

## Common questions

- **Why did a command need the network?** MiniCI runs locally, but configured
  commands retain their normal network requirements.
- **Why was a step skipped?** Check platform, branch and changed-path conditions.
- **Why is Docker unavailable?** Install/start Docker and run `minici doctor`.
- **Can two runs share one project?** MiniCI prevents overlapping runs by default.

## Project links

- Maintainer: [junjie-xu-lab](https://github.com/junjie-xu-lab)
- License: MIT
