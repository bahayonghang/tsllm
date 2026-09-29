"""Application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from importlib.metadata import version

from fastapi import FastAPI

from tsllm.runs.store import RunStore
from tsllm.service.errors import ERROR_RESPONSES, install_error_handlers
from tsllm.service.jobs import JobManager
from tsllm.service.routes import backbones, compare, datasets, runs, schema, system, templates
from tsllm.service.settings import Settings
from tsllm.service.static import mount_web


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings if settings is not None else Settings.from_env()
    store = RunStore(settings.runs_dir)
    jobs = JobManager(store, settings)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        await jobs.start()
        try:
            yield
        finally:
            await jobs.stop()

    app = FastAPI(title="tsllm", version=version("tsllm"), lifespan=lifespan)
    app.state.settings = settings
    app.state.store = store
    app.state.jobs = jobs
    install_error_handlers(app)
    for module in (system, schema, datasets, backbones, runs, compare, templates):
        app.include_router(module.router, prefix="/api", responses=ERROR_RESPONSES)
    mount_web(app, settings.web_dist)
    return app
