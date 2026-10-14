"""F3 em Asynchronous Request-Reply: o pedido vira uma tarefa em segundo plano, consultada por polling.

O estado fica em memória, no processo da aplicação (ADR 0007): perder as tarefas num reinício está
fora de escopo, e isso dispensa fila, banco ou worker a mais no compose.
"""

import threading
import uuid
from concurrent.futures import ThreadPoolExecutor

from . import report
from .ports import CapabilityUnavailable, LLMGateway, TicketSource
from .schemas import PeriodInput, TopicsReport


class TopicsJobs:
    def __init__(self, gateway: LLMGateway, tickets: TicketSource, workers: int = 2) -> None:
        self._gateway = gateway
        self._tickets = tickets
        self._executor = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="topics-job")
        self._lock = threading.Lock()
        self._jobs: dict[str, dict] = {}

    def submit(self, period: PeriodInput) -> str:
        report.validate(period)  # 422 no pedido, antes de aceitar a tarefa
        job_id = uuid.uuid4().hex[:12]
        with self._lock:
            self._jobs[job_id] = {"state": "pending", "progress": None, "reason": None, "result": None}
        self._executor.submit(self._run, job_id, period)
        return job_id

    def status(self, job_id: str) -> dict | None:
        """{"state": "pending" | "running" | "failed" | "done", "progress"?, "reason"?}, ou None."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            status = {"state": job["state"]}
            if job["progress"] is not None and job["state"] in ("running", "done"):
                status["progress"] = job["progress"]
            if job["state"] == "failed":
                status["reason"] = job["reason"]
            return status

    def result(self, job_id: str) -> TopicsReport | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job["result"] if job and job["state"] == "done" else None

    def _update(self, job_id: str, **fields) -> None:
        with self._lock:
            self._jobs[job_id].update(fields)

    def _run(self, job_id: str, period: PeriodInput) -> None:
        self._update(job_id, state="running", progress="0/?")
        try:
            result = report.topics(period, self._gateway, self._tickets,
                                   on_progress=lambda done, total: self._update(job_id, progress=f"{done}/{total}"))
        except CapabilityUnavailable as error:
            self._update(job_id, state="failed", reason=f"Capacidade {error.capability} indisponível: {error.reason}")
        except Exception as error:  # a tarefa nunca fica presa em running
            self._update(job_id, state="failed", reason=f"Erro inesperado: {type(error).__name__}")
        else:
            self._update(job_id, state="done", result=result)
