"""Same-image worker loop for queued PostgreSQL runs."""

import math
import os
import time

from caos.http import app


def dispatch_pending(store, runtime, model_runtime, futures) -> None:
    for run_id, actor in store.pending_runs():
        key = ("workflow", run_id)
        if key in futures:
            continue
        futures[key] = runtime.schedule(run_id, actor)
    if model_runtime is not None:
        for build_id, actor, kind in store.pending_model_jobs():
            key = ("model", f"{build_id}:{kind}")
            if key in futures:
                continue
            schedule = (
                model_runtime.schedule_export
                if kind == "export"
                else model_runtime.schedule
            )
            futures[key] = schedule(build_id, actor)
    for key, future in list(futures.items()):
        if not future.done():
            continue
        try:
            future.result()
        except Exception:
            print(f"CAOS worker task failed: {key[0]} {key[1]}", flush=True)
        del futures[key]


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
        dispatch_pending(store, runtime, model_runtime, futures)
        time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
