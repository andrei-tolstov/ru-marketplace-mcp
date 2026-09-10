"""Secret hygiene for Drom proxy setting."""

from __future__ import annotations

import json

from drom_connector.settings import DromSettings
from pydantic import SecretStr

SECRET_PROXY = "http://user:p/ss@proxy.example:3128"


def test_the_proxy_secret_never_appears_in_settings_dumps():
    settings = DromSettings(proxy=SecretStr(SECRET_PROXY))

    assert SECRET_PROXY not in repr(settings)
    assert SECRET_PROXY not in str(settings)
    dumped = json.dumps(settings.model_dump(mode="json"))
    assert SECRET_PROXY not in dumped
    assert "**********" in dumped


def test_the_proxy_secret_is_still_available_to_the_fetch():
    settings = DromSettings(proxy=SecretStr(SECRET_PROXY))

    assert settings.proxy.get_secret_value() == SECRET_PROXY
