# Logging Guidelines

> How progress, metrics, and diagnostics are recorded.

---

## Overview

There are 2 output paths. Use the correct one.

| Path        | API                            | Reader                                          | Content                                                           |
| ----------- | ------------------------------ | ----------------------------------------------- | ----------------------------------------------------------------- |
| Run events  | `Reporter` (`tsllm.reporting`) | User, through SSE and the web UI                | Stages, progress, metrics, user-facing messages, worker traceback |
| Diagnostics | stdlib `logging`               | Developer, through the terminal or `worker.log` | Library internals, timings, retries                               |

The CLI prints results with `typer.echo`. Library code does not call `print`.

---

## Reporter

```python
class Reporter(Protocol):
    def log(self, msg: str, level: str = "info") -> None: ...   # debug | info | warning | error
    def progress(self, step: int, total: int) -> None: ...
    def metric(self, name: str, value: float, step: int | None = None) -> None: ...
    def stage(self, name: str) -> None: ...
```

- Implementations: `NullReporter` (tests), `PrintReporter` (CLI without a run directory), `FileReporter` (`tsllm.runs.reporter`, writes `events.jsonl`).
- Data ingest, adapters, and tasks receive a `Reporter` as an argument. They do not create one and do not write files in the run directory.
- `FileReporter` writes one JSON line per call: `{"ts": "<UTC ISO>", "kind": "log|progress|metric|stage", ...}`. It calls `flush()` after each line.
- `progress` is rate-limited to 1 line per 0.5 s per stage. The last step is always written.
- Stage names: `load`, `finetune`, `evaluate:<split>`, `done`. Ingest uses `read`, `resample`, `segment`, `split`, `write`.

---

## stdlib logging

- Get a logger per module: `logger = logging.getLogger(__name__)`.
- Do not call `logging.basicConfig` in library code. The CLI and the service configure logging once at start.
- Levels:
  - `DEBUG`: shapes, batch counts, cache paths.
  - `INFO`: start and end of ingest, model load time, job start and end in the service.
  - `WARNING`: a recoverable condition that changes results (a channel with zero fit std, an all-NaN context channel).
  - `ERROR`: a job failed. Include the run id.
- Set noisy model libraries (`transformers`, `urllib3`, `huggingface_hub`) to `WARNING` in the worker.

---

## Do Not Log

- Data values from `data/` (raw rows, channel values, arrays). Log counts, shapes, row indices, and timestamps.
- Text from `ref/`.
- Secrets: `HF_TOKEN`, other tokens, credentials. `env.json` records only whether `HF_ENDPOINT` is set and its host name.
- Full file contents of configs in the service log. The run directory already holds the snapshot.

---

## Environment Snapshot

The worker writes `env.json` once per run (experiment-runner design §7): Python and platform, package versions (`null` if not installed), torch CUDA version, GPU name and compute capability, backbone checkpoint, resolved revision, and license. Every result must be traceable to this file.
