"""Generate a self-contained HTML report."""

from html import escape
from pathlib import Path

from minici.core.results import PipelineResult


def generate_report(result: PipelineResult, path: Path) -> None:
    rows = []
    for stage in result.stages:
        for step in stage.steps:
            rows.append(
                f"<tr><td>{escape(stage.name)}</td><td>{escape(step.name)}</td>"
                f"<td class='{step.status.value.lower()}'>{step.status.value}</td></tr>"
            )
    document = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>MiniCI Report</title>
<style>body{{font-family:system-ui;margin:2rem;max-width:900px}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ddd;padding:.6rem}}
.success{{color:#087f23}}.failed,.timed_out{{color:#b00020}}</style>
</head><body><h1>MiniCI Report</h1><p>Project: {escape(result.project)}</p>
<p>Status: <strong>{result.status.value}</strong></p><table><thead><tr><th>Stage</th><th>Step</th>
<th>Status</th></tr></thead><tbody>{"".join(rows)}</tbody></table></body></html>"""
    path.write_text(document, encoding="utf-8")
