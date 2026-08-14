from __future__ import annotations

import contextlib
import io
import sys
import types
import unittest
from unittest.mock import patch

from claude_daily_memory import gemini_bridge


class _Models:
    def generate_content(self, *, model: str, contents: str) -> types.SimpleNamespace:
        self.request = (model, contents)
        return types.SimpleNamespace(text="ok")


class _Client:
    def __init__(self, **kwargs: object) -> None:
        self.kwargs = kwargs
        self.models = _Models()


class GeminiBridgeTests(unittest.TestCase):
    def test_preview_does_not_import_or_send(self) -> None:
        output = io.StringIO()
        with patch.object(sys, "argv", ["gemini", "--text", "safe"]), contextlib.redirect_stdout(output):
            self.assertEqual(gemini_bridge.main(), 2)
        self.assertIn("Nothing was sent", output.getvalue())

    def test_uses_keyring_api_key_by_default(self) -> None:
        created: list[_Client] = []

        def make_client(**kwargs: object) -> _Client:
            client = _Client(**kwargs)
            created.append(client)
            return client

        fake_keyring = types.SimpleNamespace(get_password=lambda service, account: "test-key")
        fake_genai = types.SimpleNamespace(Client=make_client)
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        output = io.StringIO()
        modules = {"keyring": fake_keyring, "google": fake_google, "google.genai": fake_genai}
        argv = ["gemini", "--text", "safe", "--confirm"]
        with patch.dict(sys.modules, modules), patch.object(sys, "argv", argv), contextlib.redirect_stdout(output):
            self.assertEqual(gemini_bridge.main(), 0)
        self.assertEqual(created[0].kwargs, {"api_key": "test-key"})
        self.assertEqual(created[0].models.request, ("gemini-3.5-flash", "safe"))
        self.assertEqual(output.getvalue().strip(), "ok")

    def test_missing_key_fails_without_creating_client(self) -> None:
        fake_keyring = types.SimpleNamespace(get_password=lambda service, account: None)
        fake_genai = types.SimpleNamespace(Client=lambda **kwargs: self.fail("client created"))
        fake_google = types.ModuleType("google")
        fake_google.genai = fake_genai
        errors = io.StringIO()
        modules = {"keyring": fake_keyring, "google": fake_google, "google.genai": fake_genai}
        with (
            patch.dict(sys.modules, modules),
            patch.object(sys, "argv", ["gemini", "--text", "safe", "--confirm"]),
            contextlib.redirect_stderr(errors),
        ):
            self.assertEqual(gemini_bridge.main(), 1)
        self.assertIn("not set up", errors.getvalue())

    def test_vertex_is_used_only_when_project_is_explicit(self) -> None:
        created: list[_Client] = []
        fake_genai = types.SimpleNamespace(
            Client=lambda **kwargs: created.append(_Client(**kwargs)) or created[-1]
        )
        fake_google = types.ModuleType("google")
        fake_google.__path__ = []
        fake_google.genai = fake_genai
        fake_auth = types.ModuleType("google.auth")
        fake_auth.default = lambda **kwargs: ("credentials", "ignored")
        fake_google.auth = fake_auth
        fake_keyring = types.SimpleNamespace(get_password=lambda service, account: self.fail("keyring read"))
        modules = {
            "keyring": fake_keyring,
            "google": fake_google,
            "google.genai": fake_genai,
            "google.auth": fake_auth,
        }
        argv = ["gemini", "--project", "test-project", "--text", "safe", "--confirm"]
        with patch.dict(sys.modules, modules), patch.object(sys, "argv", argv):
            self.assertEqual(gemini_bridge.main(), 0)
        self.assertEqual(
            created[0].kwargs,
            {
                "vertexai": True,
                "credentials": "credentials",
                "project": "test-project",
                "location": "global",
            },
        )


if __name__ == "__main__":
    unittest.main()
