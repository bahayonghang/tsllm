"""Request dependencies that read the objects created by create_app."""

from typing import Annotated

from fastapi import Depends, Request

from tsllm.runs.store import RunStore
from tsllm.service.jobs import JobManager
from tsllm.service.settings import Settings


def _settings(request: Request) -> Settings:
    return request.app.state.settings


def _store(request: Request) -> RunStore:
    return request.app.state.store


def _jobs(request: Request) -> JobManager:
    return request.app.state.jobs


SettingsDep = Annotated[Settings, Depends(_settings)]
StoreDep = Annotated[RunStore, Depends(_store)]
JobsDep = Annotated[JobManager, Depends(_jobs)]
