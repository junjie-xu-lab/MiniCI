# Configuration

MiniCI uses a single strict version 1 YAML format. Unknown fields and implicit
type conversions are rejected. Commands may use an argument vector, which is
recommended for portability, or an explicit shell string.

```yaml
version: 1
project:
  name: example
defaults:
  timeout: 600
  retry: {max_attempts: 1, delay_seconds: 0}
stages:
  - name: quality
    parallel: false
    steps:
      - name: test
        commands:
          - argv: [python, -m, pytest]
```

Run `minici validate --resolved` to inspect inherited values and
`minici run --dry-run` to view the execution plan without running commands.

Steps support `retry`, `timeout`, `environment`, `working_directory`,
`continue_on_error`, local or Docker `runner`, and structured `when` conditions
for platforms and branches. A stage can set `parallel: true` and `fail_fast`.
