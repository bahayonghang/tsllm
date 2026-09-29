"""Built-in registrations expose the shared capability matrix and options."""

from tsllm.backbones import list_backbones


def test_six_backbones_match_contract() -> None:
    expected = {
        "persistence": ({"zero_shot"}, False),
        "ridge": ({"full"}, False),
        "features": (set(), True),
        "chronos2": ({"zero_shot", "lora", "full"}, True),
        "timesfm25": ({"zero_shot", "lora"}, True),
        "ttm": ({"zero_shot", "head"}, False),
    }
    registered = list_backbones()
    assert len(registered) == 6
    assert {info.name for info in registered} == set(expected)
    for info in registered:
        assert (info.capabilities.forecast_modes, info.capabilities.embed) == expected[info.name]
        for field in info.options_schema["properties"].values():
            assert field["description"]
        if info.default_checkpoint is not None:
            assert info.license == "Apache-2.0"
            assert info.license_url is not None
