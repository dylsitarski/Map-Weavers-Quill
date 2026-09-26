"""Server-only provider configuration; never part of project or API schemas."""

import os
from collections.abc import Mapping
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr

from quill.providers import ImageProvider, MockProvider


class ProviderConfigurationError(ValueError):
    """Only fixed, non-secret messages may cross this boundary."""


@dataclass(frozen=True)
class ProviderConfig:
    provider_id: str = "mock"
    api_key: SecretStr | None = field(default=None, repr=False)


def load_provider_config(environ: Mapping[str, str] | None = None) -> ProviderConfig:
    env = os.environ if environ is None else environ
    provider_id = env.get("MWQ_IMAGE_PROVIDER", "mock").strip()
    if provider_id != "mock":
        raise ProviderConfigurationError("Unsupported MWQ_IMAGE_PROVIDER; currently use mock.")
    key = env.get("MWQ_IMAGE_API_KEY")
    key_file = env.get("MWQ_IMAGE_API_KEY_FILE")
    if key is not None and key_file is not None:
        raise ProviderConfigurationError("Set only one image API key source: environment or file.")
    if key_file is not None:
        try:
            # Bounded read, no filename or OS exception details in errors.
            with Path(key_file).open("rb") as stream:
                raw = stream.read(8193)
            if len(raw) > 8192:
                raise ValueError
            key = raw.decode("utf-8")
        except (OSError, ValueError):
            raise ProviderConfigurationError("Cannot read a valid image API key file.") from None
    if key is not None:
        key = key.strip()
        if (
            not key
            or len(key.encode("utf-8")) > 8192
            or any(ord(c) < 32 or ord(c) == 127 for c in key)
        ):
            raise ProviderConfigurationError("Image API key must be a nonempty single line.")
    return ProviderConfig(provider_id, SecretStr(key) if key is not None else None)


@lru_cache(maxsize=1)
def provider_config() -> ProviderConfig:
    """One configuration snapshot per server process; restart to change it."""
    return load_provider_config()


def create_provider() -> ImageProvider:
    config = provider_config()
    if config.provider_id == "mock":
        # Fresh asset storage per operation; credentials are unused by the mock.
        return MockProvider()
    raise ProviderConfigurationError("Configured image provider is not implemented.")
