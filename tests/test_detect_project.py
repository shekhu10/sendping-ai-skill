import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "detect_project.py"


class DetectProjectTests(unittest.TestCase):
    def run_detect(self, project: Path) -> dict:
        result = subprocess.run(
            [sys.executable, str(SCRIPT), "--root", str(project)],
            check=True,
            capture_output=True,
            text=True,
        )
        return json.loads(result.stdout)

    def test_detects_next_and_existing_provider(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "package.json").write_text('{"dependencies":{"next":"16","resend":"4"}}')
            (project / "pnpm-lock.yaml").write_text("")
            (project / ".env.example").write_text("APP_URL=\n")
            (project / ".gitignore").write_text(".env*\n!.env.example\n")
            data = self.run_detect(project)
            self.assertEqual(data["languages"], ["node"])
            self.assertIn("next.js", data["frameworks"])
            self.assertEqual(data["packageManagers"], ["pnpm"])
            self.assertIn("resend", data["existingMailProviders"])
            self.assertTrue(data["environmentSecretsAppearIgnored"])

    def test_does_not_read_secret_env_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            (project / "pyproject.toml").write_text('[project]\nname="demo"\n')
            (project / ".env").write_text("MAIL_PROVIDER=secret-only-provider\n")
            data = self.run_detect(project)
            self.assertEqual(data["languages"], ["python"])
            self.assertNotIn("secret-only-provider", json.dumps(data))


if __name__ == "__main__":
    unittest.main()
