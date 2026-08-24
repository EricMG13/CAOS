"""Same-image worker loop for queued PostgreSQL runs."""

import math
import os
import time

from caos.http import app


def main() -> None:
    runtime = app.state.runtime
    model_runtime = getattr(app.state, "model_runtime", None)
    store = app.state.store
    poll_seconds = float(os.getenv("WORKER_POLL_SECONDS", "1"))
    if not math.isfinite(poll_seconds) or poll_seconds < 0.01:
        poll_seconds = 0.01
    futures = {}
    print("CAOS worker ready: PostgreSQL jobs are claimed with leases and fenced attempts.", flush=True)
    while True:
        store.refresh()
        with store.lock:
            queued = [(run["id"], run["created_by"]) for run in store.runs.values() if run["status"] in {"queued", "running"}]
            model_jobs = [
                (
                    job["build_id"],
                    store.model_builds[job["build_id"]]["created_by"],
                    job.get("kind"),
                )
                for job in getattr(store, "model_jobs", {}).values()
                if job.get("kind") in {"calculate", "export"}
                and job.get("status") in {"queued", "claimed"}
                and job.get("build_id") in getattr(store, "model_builds", {})
            ]
        for run_id, actor in queued:
            key = ("workflow", run_id)
            if key not in futures:
                futures[key] = runtime.executor.submit(runtime._execute, run_id, actor)
        for build_id, actor, kind in (model_jobs if model_runtime is not None else ()):
            key = ("model", f"{build_id}:{kind}")
            if key not in futures:
                execute = model_runtime._execute_export if kind == "export" else model_runtime._execute
                futures[key] = runtime.executor.submit(execute, build_id, actor)
        for key, future in list(futures.items()):
            if future.done():
                try:
                    future.result()
                except Exception:
                    print(f"CAOS worker task failed: {key[0]} {key[1]}", flush=True)
                del futures[key]
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
