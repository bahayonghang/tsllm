"""Channel dictionary edits that keep the channel set of a dataset."""

from pathlib import Path

from tsllm.config.dataset import ChannelSpec, DatasetConfig
from tsllm.data.cache import read_meta
from tsllm.data.registry import ChannelError, load_dataset, save_dataset


def update_channels(
    dataset_id: str,
    updates: list[ChannelSpec],
    directory: Path | None = None,
    cache_root: Path | None = None,
) -> DatasetConfig:
    """Change channel role, unit, and description, then write the dataset YAML file.

    A config with automatic channel discovery gets its channel list from a fresh cache.
    The channel order of the original config is kept.
    """
    cfg = load_dataset(dataset_id, directory)
    if cfg.channels is not None:
        current = cfg.channels
    else:
        meta = read_meta(cfg, cache_root)
        if meta is None:
            raise ChannelError(
                f"dataset '{dataset_id}' discovers channels automatically; ingest it first"
            )
        current = [ChannelSpec(name=name) for name in meta["channel_names"]]
    by_name = {ch.name: ch for ch in updates}
    if len(by_name) != len(updates) or set(by_name) != {ch.name for ch in current}:
        raise ChannelError(f"dataset '{dataset_id}' channel names must match the configuration")
    try:
        updated = DatasetConfig.model_validate(
            cfg.model_dump() | {"channels": [by_name[ch.name].model_dump() for ch in current]}
        )
    except ValueError:
        # Validation messages name the rule, not source values.
        raise ChannelError(f"dataset '{dataset_id}' channel roles are invalid") from None
    save_dataset(updated, directory)
    return updated
