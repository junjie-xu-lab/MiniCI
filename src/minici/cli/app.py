"""MiniCI command-line entry point."""

from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from minici.application.pipeline import PipelineService
from minici.config.loader import ConfigError, load_config
from minici.config.template import DEFAULT_CONFIG
from minici.integrations.git import inspect_git
from minici.plugins import discover_plugins
from minici.triggers.watch import changes
from minici.version import __version__

app = typer.Typer(
    name="minici",
    help="Run local CI/CD pipelines without a server.",
    no_args_is_help=True,
    add_completion=False,
)
console = Console()


@app.callback()
def main() -> None:
    """Run local CI/CD pipelines without a server."""


@app.command("init")
def init_project(
    force: Annotated[bool, typer.Option("--force", help="Overwrite an existing file.")] = False,
) -> None:
    """Create a default minici.yml in the current directory."""
    path = Path.cwd() / "minici.yml"
    if path.exists() and not force:
        console.print(f"[red]Configuration already exists:[/] {path}")
        raise typer.Exit(code=2)
    path.write_text(DEFAULT_CONFIG, encoding="utf-8")
    console.print(f"[green]Created[/] {path}")


@app.command()
def validate(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("minici.yml"),
    resolved: Annotated[bool, typer.Option("--resolved")] = False,
) -> None:
    """Validate a pipeline configuration without running commands."""
    parsed = _load_or_exit(config)
    console.print(f"[green]Valid[/] {config}")
    if resolved:
        for item in parsed.resolved_steps(config.resolve().parent):
            console.print(
                f"- {item['stage']} / {item['step']} | runner={item['runner']} "
                f"timeout={item['timeout']}s attempts={item['max_attempts']}"
            )


@app.command()
def run(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("minici.yml"),
    dry_run: Annotated[bool, typer.Option("--dry-run")] = False,
) -> None:
    """Run a pipeline, or display its resolved plan."""
    parsed = _load_or_exit(config)
    if dry_run:
        console.print(f"[bold]Dry run:[/] {parsed.project.name}")
        for item in parsed.resolved_steps(config.resolve().parent):
            mode = "parallel" if item["parallel"] else "sequential"
            console.print(f"[{mode}] {item['stage']} / {item['step']} ({item['runner']})")
            for command in item["commands"]:
                console.print(f"  $ {command}")
        return
    try:
        result = PipelineService(config.resolve().parent).execute(parsed)
    except RuntimeError as exc:
        console.print(f"[red]Run error:[/] {exc}")
        raise typer.Exit(code=2) from exc
    style = "green" if result.status.value == "SUCCESS" else "red"
    console.print(f"[{style}]{result.status.value}[/] Run #{result.run_id}")
    raise typer.Exit(code=0 if result.status.value == "SUCCESS" else 1)


@app.command()
def status(
    limit: Annotated[int, typer.Option("--limit", min=1, max=100)] = 10,
    project: Annotated[Path, typer.Option("--project")] = Path("."),
) -> None:
    """Show recent pipeline runs."""
    rows = PipelineService(project).repository.recent(limit)
    if not rows:
        console.print("No MiniCI runs found.")
        return
    table = Table("ID", "Project", "Status", "Started", "Duration")
    for row in rows:
        duration = "-" if row["duration"] is None else f"{row['duration']:.2f}s"
        table.add_row(str(row["id"]), row["project"], row["status"], row["started_at"], duration)
    console.print(table)


@app.command()
def logs(
    run_id: int,
    project: Annotated[Path, typer.Option("--project")] = Path("."),
) -> None:
    """Print the log for a run."""
    row = _find_run(project, run_id)
    path = Path(row["run_directory"]) / "run.log"
    console.print(path.read_text(encoding="utf-8"), markup=False)


@app.command()
def report(
    run_id: int,
    project: Annotated[Path, typer.Option("--project")] = Path("."),
) -> None:
    """Show the generated report path for a run."""
    row = _find_run(project, run_id)
    path = Path(row["run_directory"]) / "report.html"
    console.print(path)


@app.command()
def doctor(project: Annotated[Path, typer.Option("--project")] = Path(".")) -> None:
    """Check local tools and MiniCI storage."""
    import shutil

    git = inspect_git(project.resolve())
    console.print(f"MiniCI {__version__}")
    console.print(f"Git: {'available' if git.available else 'unavailable'}")
    console.print(f"Docker: {'available' if shutil.which('docker') else 'unavailable (optional)'}")
    console.print(f"Data: {(project.resolve() / '.minici')}")
    try:
        plugins = discover_plugins()
        console.print(f"Plugins: {len(plugins)}")
    except RuntimeError as exc:
        console.print(f"[red]Plugin error:[/] {exc}")
        raise typer.Exit(code=2) from exc


@app.command()
def dashboard(
    project: Annotated[Path, typer.Option("--project")] = Path("."),
    host: Annotated[str, typer.Option("--host")] = "127.0.0.1",
    port: Annotated[int, typer.Option("--port", min=1, max=65535)] = 8765,
) -> None:
    """Start the local dashboard."""
    import uvicorn

    from minici.web.app import create_app

    if host != "127.0.0.1":
        console.print("[yellow]Warning: the dashboard has no authentication.[/]")
    uvicorn.run(create_app(project.resolve()), host=host, port=port)


@app.command("plugin-list")
def plugin_list() -> None:
    """List enabled Python entry-point plugins."""
    plugins = discover_plugins()
    if not plugins:
        console.print("No plugins installed.")
    for plugin in plugins:
        console.print(f"{plugin.name} (API {plugin.api_version})")


@app.command()
def watch(
    config: Annotated[Path, typer.Option("--config", "-c")] = Path("minici.yml"),
) -> None:
    """Run the pipeline when project files change."""
    parsed = _load_or_exit(config)
    root = config.resolve().parent
    debounce = parsed.triggers.watch.debounce_ms if parsed.triggers.watch else 800
    console.print(f"Watching {root} (Ctrl+C to stop)")
    try:
        watch_config = parsed.triggers.watch
        include = watch_config.include if watch_config else None
        exclude = watch_config.exclude if watch_config else None
        for _ in changes(root, debounce, include, exclude):
            result = PipelineService(root).execute(parsed)
            console.print(f"Run #{result.run_id}: {result.status.value}")
    except KeyboardInterrupt:
        console.print("Watch stopped.")


def _find_run(project: Path, run_id: int):
    rows = PipelineService(project).repository.recent(100)
    for row in rows:
        if row["id"] == run_id:
            return row
    console.print(f"[red]Run not found:[/] {run_id}")
    raise typer.Exit(code=2)


def _load_or_exit(config: Path):
    try:
        return load_config(config)
    except ConfigError as exc:
        console.print(f"[red]Configuration error:[/] {exc}")
        raise typer.Exit(code=2) from exc


@app.command()
def version(
    verbose: Annotated[
        bool,
        typer.Option("--verbose", help="Show additional build information."),
    ] = False,
) -> None:
    """Show the installed MiniCI version."""
    console.print(f"MiniCI {__version__}")
    if verbose:
        import platform
        import sys

        console.print(f"Python {platform.python_version()}")
        console.print(f"Platform {platform.system()} {platform.machine()}")
        console.print(f"Executable {sys.executable}")
