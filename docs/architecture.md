# Architecture

MiniCI separates command-line and dashboard adapters from a shared application
service, scheduler, runners, event consumers, and persistence layer. Detailed
contracts share strict Pydantic models and immutable execution results. A project
lock prevents overlapping runs. SQLite stores structured summaries, while the
run log remains the full output source. Dashboard and CLI call the same
`PipelineService`; Docker and plugins are optional boundaries.
