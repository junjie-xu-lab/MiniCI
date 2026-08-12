"""Default version 1 configuration template."""

DEFAULT_CONFIG = """version: 1

project:
  name: my-project

defaults:
  timeout: 600
  retry:
    max_attempts: 1
    delay_seconds: 0

stages:
  - name: quality
    parallel: false
    steps:
      - name: test
        commands:
          - run: echo MiniCI pipeline ready
"""
