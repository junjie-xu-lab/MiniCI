# Security policy

## Trust boundary

A MiniCI configuration can execute commands with the permissions of the current
user. Only run configurations and plugins from sources you trust. MiniCI is not
a security sandbox and never elevates privileges automatically.

The local dashboard binds to `127.0.0.1` by default. Do not expose it to an
untrusted network.

## Reporting a vulnerability

Please report vulnerabilities privately through the repository's GitHub security
advisory feature. Do not include credentials, tokens, or private project data.

