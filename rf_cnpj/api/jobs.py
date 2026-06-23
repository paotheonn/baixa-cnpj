from __future__ import annotations

from queue import Queue
from threading import Thread
from uuid import uuid4

from rf_cnpj.core.events import PipelineEvent, build_event
from rf_cnpj.core.models import ExportResult, RunConfig
from rf_cnpj.core.processor import PipelineRunner

TERMINAL_EVENTS = {"done", "error"}


class RunJob:
    def __init__(self, run_id: str):
        self.run_id = run_id
        self.events: Queue[PipelineEvent | None] = Queue()
        self.last_type: str | None = None

    def emit(self, event: PipelineEvent) -> None:
        self.last_type = event["type"]
        self.events.put(event)

    def finish(self) -> None:
        self.events.put(None)


class RunJobManager:
    def __init__(self, runner: PipelineRunner):
        self.runner = runner
        self.jobs: dict[str, RunJob] = {}

    def start(self, config: RunConfig) -> str:
        run_id = uuid4().hex
        job = RunJob(run_id)
        self.jobs[run_id] = job
        Thread(target=self._run, args=(job, config), daemon=True).start()
        return run_id

    def get(self, run_id: str) -> RunJob | None:
        return self.jobs.get(run_id)

    def _run(self, job: RunJob, config: RunConfig) -> None:
        try:
            result = self.runner.run(config, emit=job.emit)
            if job.last_type != "done":
                job.emit(_done_event(result))
        except Exception as exc:
            if job.last_type != "error":
                job.emit(build_event("error", f"Erro na pipeline: {exc}", level="error", data={"error": str(exc)}))
        finally:
            job.finish()


def _done_event(result: ExportResult) -> PipelineEvent:
    return build_event(
        "done",
        "Pipeline concluida",
        level="success",
        data={
            "csv_path": result.csv_path.as_posix(),
            "parquet_path": result.parquet_path.as_posix(),
            "rows": result.rows,
        },
    )
