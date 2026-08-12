"""FastAPI dashboard, local-only by default."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse

from minici.application.pipeline import PipelineService
from minici.config.loader import ConfigError, load_config


def create_app(project_root: Path) -> FastAPI:
    app = FastAPI(title="MiniCI Dashboard")
    service = PipelineService(project_root)

    @app.get("/", response_class=HTMLResponse)
    def index() -> str:
        return """<!doctype html><html><head><meta charset="utf-8">
<title>MiniCI Dashboard</title><style>
body{font-family:system-ui;max-width:960px;margin:2rem auto;padding:0 1rem;color:#202124}
button{padding:.55rem .8rem;margin-right:.5rem}
table{border-collapse:collapse;width:100%;margin-top:1rem}
th,td{text-align:left;padding:.65rem;border-bottom:1px solid #ddd}
.SUCCESS{color:#087f23}.FAILED{color:#b00020}
</style></head><body><h1>MiniCI Dashboard</h1><p>Local pipeline history</p>
<button onclick="runPipeline()">Run pipeline</button><button onclick="cancelRun()">Cancel</button>
<span id="message"></span><table><thead><tr><th>ID</th><th>Project</th><th>Status</th>
<th>Started</th><th>Duration</th></tr></thead><tbody id="runs"></tbody></table>
<script>
async function refresh(){const rows=await(await fetch('/api/runs')).json();
document.getElementById('runs').innerHTML=rows.map(r=>`<tr><td>${r.id}</td><td>${escapeHtml(r.project)}</td>
<td class="${r.status}">${r.status}</td><td>${r.started_at}</td>
<td>${r.duration??'-'}</td></tr>`).join('')}
function escapeHtml(v){const e=document.createElement('div');e.textContent=v;return e.innerHTML}
async function runPipeline(){message('Running...');const r=await fetch('/api/run',{method:'POST'});
message(r.ok?'Run finished':(await r.json()).detail);await refresh()}
async function cancelRun(){await fetch('/api/cancel',{method:'POST'});
message('Cancellation requested')}
function message(v){document.getElementById('message').textContent=v}
refresh();setInterval(refresh,2000)
</script></body></html>"""

    @app.get("/api/runs")
    def runs(limit: int = 20) -> list[dict[str, object]]:
        if not 1 <= limit <= 100:
            raise HTTPException(400, "limit must be between 1 and 100")
        return [dict(row) for row in service.repository.recent(limit)]

    @app.get("/api/runs/{run_id}")
    def run_details(run_id: int) -> dict[str, object]:
        details = service.repository.details(run_id)
        if details is None:
            raise HTTPException(404, "run not found")
        return details

    @app.get("/api/runs/{run_id}/logs")
    def run_logs(run_id: int, offset: int = 0) -> dict[str, object]:
        details = service.repository.details(run_id)
        if details is None:
            raise HTTPException(404, "run not found")
        run_directory = Path(str(details["run"]["run_directory"])).resolve()
        allowed_root = (project_root / ".minici" / "runs").resolve()
        if allowed_root not in run_directory.parents:
            raise HTTPException(403, "invalid run path")
        log_path = run_directory / "run.log"
        content = log_path.read_text(encoding="utf-8") if log_path.exists() else ""
        safe_offset = max(0, min(offset, len(content)))
        return {"offset": len(content), "content": content[safe_offset:]}

    @app.post("/api/run")
    def run_pipeline() -> dict[str, object]:
        config_path = project_root / "minici.yml"
        try:
            config = load_config(config_path)
            result = service.execute(config)
        except (ConfigError, RuntimeError) as exc:
            raise HTTPException(409, str(exc)) from exc
        return {"id": result.run_id, "status": result.status.value}

    @app.post("/api/cancel")
    def cancel_pipeline() -> dict[str, str]:
        service.cancel()
        return {"status": "cancellation requested"}

    return app
