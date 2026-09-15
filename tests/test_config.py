import pytest

import config


@pytest.mark.parametrize("value", [None, "", "   "])
def test_production_required_env_rejects_missing_or_blank(monkeypatch, value):
    monkeypatch.setattr(config, "IS_PRODUCTION", True)
    if value is None:
        monkeypatch.delenv("AG_DB_PWD", raising=False)
    else:
        monkeypatch.setenv("AG_DB_PWD", value)

    with pytest.raises(RuntimeError, match="AG_DB_PWD must be set"):
        config._env("AG_DB_PWD", required_in_prod=True)
