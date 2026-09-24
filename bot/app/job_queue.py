from __future__ import annotations

import asyncio
import itertools
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any

from app.settings import settings
from app.user_files import UserJobDir

log = logging.getLogger("teradrop.queue")


@dataclass
class _Job:
    priority: int
    sequence: int
    user_id: int
    job_id: str
    kind: str
    operation: Callable[[], Awaitable[Any]]
    future: asyncio.Future
    queued_at: float = field(default_factory=time.monotonic)


class UserGate:
    """Atomic per-user in-flight counter. Free users get one slot; premium
    users are capped at their batch limit so one account cannot starve others.
    """

    def __init__(self) -> None:
        self._active: dict[int, int] = {}
        self._lock = asyncio.Lock()

    def snapshot(self) -> dict[int, int]:
        return dict(self._active)

    async def try_enter(self, user_id: int, limit: int) -> bool:
        limit = max(1, int(limit))
        async with self._lock:
            current = self._active.get(user_id, 0)
            if current >= limit:
                return False
            self._active[user_id] = current + 1
            return True

    async def exit(self, user_id: int) -> None:
        async with self._lock:
            current = self._active.get(user_id, 0) - 1
            if current <= 0:
                self._active.pop(user_id, None)
            else:
                self._active[user_id] = current


class PriorityJobQueue:
    """Bounded priority queue with per-user isolation metadata.

    VIP / Super / Regular jobs run ahead of free jobs. Each job records the
    owning user so admin tooling can see who is on which worker. Worker count
    can be resized live when MAX_CONCURRENT is updated from the admin panel.
    """

    def __init__(self) -> None:
        self._queue: asyncio.PriorityQueue[tuple[int, int, _Job]] = asyncio.PriorityQueue(
            maxsize=max(10, settings.max_queue_size)
        )
        self._sequence = itertools.count()
        self._workers: list[asyncio.Task] = []
        self._started = False
        self._active_jobs: dict[str, dict[str, Any]] = {}
        self._completed = 0
        self._failed = 0
        self._lock = asyncio.Lock()
        self._reaper: asyncio.Task | None = None

    async def start(self) -> None:
        if self._started:
            return
        self._started = True
        for index in range(max(1, min(settings.max_concurrent, 64))):
            self._workers.append(asyncio.create_task(self._worker(index)))
        self._reaper = asyncio.create_task(self._reap_loop())

    async def stop(self) -> None:
        for worker in self._workers:
            worker.cancel()
        if self._reaper:
            self._reaper.cancel()
            self._workers.append(self._reaper)
        await asyncio.gather(*self._workers, return_exceptions=True)
        self._workers.clear()
        self._reaper = None
        self._started = False

    async def resize(self, worker_count: int) -> None:
        worker_count = max(1, min(int(worker_count), 64))
        if not self._started:
            settings.max_concurrent = worker_count
            return
        current = len(self._workers)
        if worker_count > current:
            for index in range(current, worker_count):
                self._workers.append(asyncio.create_task(self._worker(index)))
        elif worker_count < current:
            extra = self._workers[worker_count:]
            self._workers = self._workers[:worker_count]
            for task in extra:
                task.cancel()
            await asyncio.gather(*extra, return_exceptions=True)
        settings.max_concurrent = worker_count

    async def submit(
        self,
        priority: int,
        operation: Callable[[], Awaitable[Any]],
        *,
        user_id: int = 0,
        kind: str = "job",
    ) -> Any:
        if not self._started:
            await self.start()
        if self._queue.full():
            raise RuntimeError("the processing queue is full. retry in a moment or upgrade for priority access.")
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        job = _Job(
            priority=priority,
            sequence=next(self._sequence),
            user_id=int(user_id),
            job_id=f"{int(user_id)}-{secrets_hex()}",
            kind=kind,
            operation=operation,
            future=future,
        )
        await self._queue.put((job.priority, job.sequence, job))
        return await future

    def size(self) -> int:
        return self._queue.qsize()

    def snapshot(self) -> dict[str, Any]:
        return {
            "queued": self._queue.qsize(),
            "workers": len(self._workers),
            "active": list(self._active_jobs.values()),
            "completed": self._completed,
            "failed": self._failed,
            "user_inflight": USER_GATE.snapshot(),
        }

    async def _worker(self, index: int) -> None:
        while True:
            _, _, job = await self._queue.get()
            record = {
                "job_id": job.job_id,
                "user_id": job.user_id,
                "kind": job.kind,
                "worker": index,
                "waited_ms": int((time.monotonic() - job.queued_at) * 1000),
                "started_at": time.time(),
            }
            async with self._lock:
                self._active_jobs[job.job_id] = record
            try:
                if not job.future.cancelled():
                    job.future.set_result(await job.operation())
                async with self._lock:
                    self._completed += 1
            except asyncio.CancelledError:
                if not job.future.done():
                    job.future.cancel()
                raise
            except Exception as exc:
                async with self._lock:
                    self._failed += 1
                if not job.future.done():
                    job.future.set_exception(exc)
                log.exception("worker %s failed job %s user %s", index, job.job_id, job.user_id)
            finally:
                async with self._lock:
                    self._active_jobs.pop(job.job_id, None)
                self._queue.task_done()

    async def _reap_loop(self) -> None:
        while True:
            await asyncio.sleep(600)
            try:
                removed = UserJobDir.reap_stale()
                if removed:
                    log.info("reaped %s stale download directories", removed)
            except Exception:
                log.exception("stale-file reaper failed")


def secrets_hex() -> str:
    import secrets

    return secrets.token_hex(4)


JOB_QUEUE = PriorityJobQueue()
USER_GATE = UserGate()


def priority_for(access: dict[str, Any]) -> int:
    if not access.get("premium"):
        return 30
    return {"v": 0, "s": 10, "r": 20}.get(str(access.get("plan_key")), 20)


def slot_limit_for(access: dict[str, Any]) -> int:
    if not access.get("premium"):
        return 1
    return max(1, min(int(access.get("batch_limit") or 2), 16))
