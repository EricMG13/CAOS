"""Same-image worker loop for queued PostgreSQL runs."""

import os
import time

from caos.http import app


def main() -> None:
    runtime = app.state.runtime
    store = app.state.store
    poll_seconds = float(os.getenv("WORKER_POLL_SECONDS", "1"))
    futures = {}
    print("CAOS worker ready: PostgreSQL jobs are claimed with leases and fenced attempts.", flush=True)
    while True:
        store.refresh()
        with store.lock:
            queued = [(run["id"], run["created_by"]) for run in store.runs.values() if run["status"] in {"queued", "running"}]
        for run_id, actor in queued:
            if run_id not in futures:
                futures[run_id] = runtime.executor.submit(runtime._execute, run_id, actor)
        for run_id, future in list(futures.items()):
            if future.done():
                future.result()
                del futures[run_id]
        if not queued and not futures:
            time.sleep(poll_seconds)


if __name__ == "__main__":
    main()
