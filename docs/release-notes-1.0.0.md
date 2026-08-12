# MiniCI 1.0.0

The first stable MiniCI release provides local-first CI/CD pipelines without a
server or hosted account.

Highlights:

- Strict versioned YAML, dry-run planning, retries, parallel stages and conditions.
- Local subprocess and optional Docker runners.
- SQLite history, redacted logs and offline HTML reports.
- Git metadata, file watching, local Dashboard and versioned plugin discovery.
- Python package and tested Windows x64 standalone executable.

Known limits:

- Docker could not be exercised on the release workstation because Docker is absent.
- Standalone binaries only support plugins bundled at build time.
- macOS and Linux artifacts must be built on their respective platforms.
