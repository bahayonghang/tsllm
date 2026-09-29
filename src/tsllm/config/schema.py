"""JSON Schema export for run forms."""

from typing import Any

from tsllm.config.run import RunConfig


def run_config_schema() -> dict[str, Any]:
    from tsllm.backbones import list_backbones

    return {
        "run_config": RunConfig.model_json_schema(),
        "backbone_options": {info.name: info.options_schema for info in list_backbones()},
    }
