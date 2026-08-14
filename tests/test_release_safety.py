from __future__ import annotations

import re
import subprocess
import tomllib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ReleaseSafetyTests(unittest.TestCase):
    def test_notebooklm_credentials_are_explicitly_ignored(self) -> None:
        ignored = (ROOT / ".gitignore").read_text(encoding="utf-8")
        for pattern in (
            ".notebooklm/",
            "storage_state.json",
            "master_token.json",
            "browser_profile/",
        ):
            self.assertIn(pattern, ignored)

    def test_notebooklm_dependency_is_exactly_pinned(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        self.assertEqual(
            project["project"]["optional-dependencies"]["notebooklm"],
            ["notebooklm-py[browser,mcp]==0.8.0"],
        )

    def test_release_version_is_consistent(self) -> None:
        project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
        citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
        package = (ROOT / "src/claude_daily_memory/__init__.py").read_text(encoding="utf-8")
        version = project["project"]["version"]
        self.assertEqual(version, "0.2.0")
        self.assertIn(f"version: {version}", citation)
        self.assertIn(f'__version__ = "{version}"', package)

    @staticmethod
    def _release_paths() -> list[str]:
        return subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
            cwd=ROOT,
            check=True,
            text=True,
            capture_output=True,
        ).stdout.splitlines()

    def test_tracked_files_do_not_include_auth_artifacts(self) -> None:
        forbidden_names = {
            "storage_state.json",
            "master_token.json",
            "google-client.json",
            "token.json",
        }
        for path in self._release_paths():
            parts = Path(path).parts
            self.assertFalse(".notebooklm" in parts or forbidden_names.intersection(parts), path)

    def test_release_files_contain_only_exact_synthetic_secret_fixtures(self) -> None:
        patterns = {
            "private-key": re.compile("-----BEGIN " + "PRIVATE KEY-----"),
            "google-api-key": re.compile("AI" + r"za[0-9A-Za-z_-]{30,}"),
            "oauth-access-token": re.compile("ya" + r"29\.[0-9A-Za-z_-]{20,}"),
            "github-token": re.compile("gh" + r"[opsu]_[0-9A-Za-z]{20,}"),
            "anthropic-key": re.compile("sk-" + r"ant-[0-9A-Za-z_-]{20,}"),
            "personal-home": re.compile("/home/" + r"geft2(?:/|\b)"),
            "email": re.compile(
                r"(?<![\w.+-])[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}(?![\w.-])"
            ),
        }
        synthetic = {
            ("tests/test_digest.py", "github-token"): {
                "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEF123456"
            },
            ("tests/test_sanitize.py", "private-key"): {
                "-----BEGIN " + "PRIVATE KEY-----"
            },
            ("tests/test_sanitize.py", "google-api-key"): {
                "AI" + "zaSyDUMMYDUMMYDUMMYDUMMYDUMMYDUMMY1"
            },
            ("tests/test_sanitize.py", "github-token"): {
                "ghp_" + "abcdefghijklmnopqrstuvwxyzABCDEF123456"
            },
        }
        problems: list[str] = []
        for relative in self._release_paths():
            path = ROOT / relative
            if not path.is_file():
                continue
            try:
                text = path.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            for name, pattern in patterns.items():
                for match in pattern.findall(text):
                    if name == "email" and match.rsplit("@", 1)[1] in {
                        "example.com",
                        "news.example",
                        "newsletters.example",
                        "example.invalid",
                    }:
                        continue
                    if match in synthetic.get((relative, name), set()):
                        continue
                    problems.append(f"{relative}: {name}")
        self.assertEqual(problems, [])

    def test_supported_code_does_not_enable_remote_notebooklm_auth(self) -> None:
        files = [ROOT / "install.sh"] + sorted((ROOT / "src").rglob("*.py"))
        content = "\n".join(path.read_text(encoding="utf-8") for path in files)
        for forbidden in (
            "NOTEBOOKLM_AUTH_JSON",
            "--master-token",
            "--transport http",
            "notebooklm-server",
        ):
            self.assertNotIn(forbidden, content)

    def test_public_docs_describe_complete_notebooklm_memory(self) -> None:
        english = (ROOT / "README.md").read_text(encoding="utf-8")
        russian = (ROOT / "README-RU.md").read_text(encoding="utf-8")
        for text in (english, russian):
            self.assertRegex(text, re.compile(r"all .*notebook|все .*блокнот", re.IGNORECASE))
            self.assertRegex(text, re.compile(r"automatic.*refresh|автоматическ.*обнов", re.IGNORECASE))
        self.assertNotIn("Add that document once to NotebookLM", english)
        self.assertNotIn("Один раз добавьте его в NotebookLM", russian)

    def test_ci_verifies_complete_release_on_supported_python_versions(self) -> None:
        workflow = (ROOT / ".github" / "workflows" / "tests.yml").read_text(
            encoding="utf-8"
        )
        for version in ('"3.11"', '"3.12"', '"3.13"'):
            self.assertIn(version, workflow)
        for contract in (
            ".[google,gemini,notebooklm]",
            "python -m unittest discover -s tests",
            "python -m build",
            "python -m pip check",
            "test_installer.py",
            "test_release_safety.py",
        ):
            self.assertIn(contract, workflow)
        self.assertRegex(workflow, re.compile(r"wheel.*venv|venv.*wheel", re.IGNORECASE))

    def test_python_313_is_declared_supported(self) -> None:
        project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn("Programming Language :: Python :: 3.13", project)


if __name__ == "__main__":
    unittest.main()
