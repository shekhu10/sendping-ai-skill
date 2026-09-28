import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("verify_setup", ROOT / "scripts" / "verify_setup.py")
verify_setup = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = verify_setup
SPEC.loader.exec_module(verify_setup)


class VerifySetupTests(unittest.TestCase):
    def project(self):
        return tempfile.TemporaryDirectory()

    def test_good_server_integration_has_no_errors(self):
        with self.project() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text(".env*\n!.env.example\n")
            (root / ".env.example").write_text("SENDPING_API_KEY=\nSENDPING_FROM=\n")
            (root / "package.json").write_text('{"dependencies":{"sendping":"^1.0.0"}}')
            (root / "mail-service.ts").write_text(
                "import { SendPing } from 'sendping';\n"
                "const client = new SendPing(process.env.SENDPING_API_KEY!);\n"
                "client.emails.send(payload, { idempotencyKey: operationId });\n"
                "const from = process.env.SENDPING_FROM;\n"
            )
            findings = verify_setup.audit(root)
            self.assertFalse([item for item in findings if item.level == "error"])

    def test_flags_public_and_literal_secrets(self):
        with self.project() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text(".env*\n")
            (root / "client.ts").write_text(
                "const key = process.env.NEXT_PUBLIC_SENDPING_API_KEY;\n"
                "const leaked = 'mb_abcdefghijklmnopqrstuvwxyzABCDEF';\n"
            )
            codes = {item.code for item in verify_setup.audit(root)}
            self.assertIn("client_exposed_secret", codes)
            self.assertIn("exposed_api_key", codes)

    def test_webhook_requires_complete_verification_contract(self):
        with self.project() as tmp:
            root = Path(tmp)
            (root / ".gitignore").write_text(".env*\n")
            (root / "webhook.ts").write_text(
                "const secret = process.env.SENDPING_WEBHOOK_SECRET;\n"
                "const id = headers.get('svix-id');\n"
            )
            codes = {item.code for item in verify_setup.audit(root)}
            self.assertIn("incomplete_webhook_verification", codes)


if __name__ == "__main__":
    unittest.main()
