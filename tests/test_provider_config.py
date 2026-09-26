"""Offline server configuration and secret-boundary regressions."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from quill.main import app
from quill.provider_config import (
    ProviderConfigurationError,
    create_provider,
    load_provider_config,
    provider_config,
)


class ProviderConfigTests(unittest.TestCase):
    def tearDown(self):
        provider_config.cache_clear()

    def test_default_and_isolated_operation_assets(self):
        with patch.dict("os.environ", {}, clear=True):
            provider_config.cache_clear()
            self.assertEqual(load_provider_config().provider_id, "mock")
            first, second = create_provider(), create_provider()
            first.put(b"synthetic asset")
            self.assertEqual(second.assets, {})

    def test_secret_sources_and_redaction(self):
        secret = "synthetic-test-key"
        direct = load_provider_config({"MWQ_IMAGE_API_KEY": secret})
        self.assertEqual(direct.api_key.get_secret_value(), secret)
        self.assertNotIn(secret, repr(direct))
        self.assertNotIn(secret, str(direct.api_key))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "key"
            path.write_text(secret + "\n")
            config = load_provider_config({"MWQ_IMAGE_API_KEY_FILE": str(path)})
            self.assertEqual(config.api_key.get_secret_value(), secret)
            path.write_bytes(b"x" * 8193)
            with self.assertRaises(ProviderConfigurationError):
                load_provider_config({"MWQ_IMAGE_API_KEY_FILE": str(path)})
            path.write_bytes(b"\xff")
            with self.assertRaises(ProviderConfigurationError):
                load_provider_config({"MWQ_IMAGE_API_KEY_FILE": str(path)})

    def test_bad_configuration_fails_without_echoing_values(self):
        cases = [
            {"MWQ_IMAGE_PROVIDER": "private-provider-name"},
            {"MWQ_IMAGE_API_KEY": "private-key", "MWQ_IMAGE_API_KEY_FILE": "/private/path"},
            {"MWQ_IMAGE_API_KEY_FILE": "/nonexistent/private/path"},
            {"MWQ_IMAGE_API_KEY": ""},
            {"MWQ_IMAGE_API_KEY": "private\nkey"},
            {"MWQ_IMAGE_API_KEY": "x" * 8193},
        ]
        for env in cases:
            with (
                self.subTest(keys=list(env)),
                self.assertRaises(ProviderConfigurationError) as error,
            ):
                load_provider_config(env)
            self.assertNotIn("private", str(error.exception))

    def test_invalid_config_prevents_queue_startup(self):
        with (
            patch.dict("os.environ", {"MWQ_IMAGE_PROVIDER": "unknown"}, clear=True),
            patch("quill.main.JobService") as queue,
        ):
            provider_config.cache_clear()
            with self.assertRaises(ProviderConfigurationError), TestClient(app):
                pass
            queue.assert_not_called()

    def test_configuration_is_frozen_and_discovery_is_allowlisted(self):
        with (
            tempfile.TemporaryDirectory() as directory,
            patch.dict(
                "os.environ",
                {"MWQ_DATA_DIR": directory, "MWQ_IMAGE_API_KEY": "synthetic-test-key"},
                clear=True,
            ),
        ):
            provider_config.cache_clear()
            with TestClient(app) as client:
                with patch.dict("os.environ", {"MWQ_IMAGE_PROVIDER": "unknown"}):
                    response = client.get("/api/providers")
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.json()[0]["id"], "mock")
                    self.assertNotIn("synthetic-test-key", response.text)
                    self.assertEqual(
                        set(response.json()[0]),
                        {"contractVersion", "id", "capabilities", "maxWidth", "maxHeight", "local"},
                    )
