import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "skills/impo-gadget-developer/scripts/impo.py"
spec = importlib.util.spec_from_file_location("impo", SCRIPT)
impo = importlib.util.module_from_spec(spec)
spec.loader.exec_module(impo)
PRODUCT = "6f1c2b9e-4a7d-4e2b-9c1a-3d5e7f9a1b2c"


class ManifestTests(unittest.TestCase):
    def run_cli(self, args, response):
        output = io.StringIO()
        with patch.dict(os.environ, {"IMPO_API_KEY": "impo_dev_test"}), \
                patch("sys.argv", ["impo.py", *args]), \
                patch.object(impo, "call", return_value=response) as call, \
                contextlib.redirect_stdout(output):
            impo.main()
        return output.getvalue(), call.call_args.args

    def test_pull_edit_preview_and_push_preserve_scenarios(self):
        scenario = {"name": "Focused work", "when": "Work starts", "instructions": "Turn on the lamp."}
        manifest = {"minFirmware": "0", "systemPrompt": "A lamp.", "commands": [], "events": [],
                    "scenarios": [scenario], "revision": 2, "instructions": "Derived text"}
        pulled, _ = self.run_cli(["manifest", "pull", PRODUCT], {"manifests": {"dev": [manifest]}})
        content = json.loads(pulled)
        self.assertEqual(content["scenarios"], [scenario])
        self.assertNotIn("revision", content)
        self.assertNotIn("instructions", content)
        content["scenarios"][0]["instructions"] = "Turn off the lamp."
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(content))
            _, preview = self.run_cli(["manifest", "preview", str(path)], {"instructions": "Preview"})
            _, pushed = self.run_cli(["manifest", "push", str(path)],
                                     {"manifest": {"revision": 3}, "delivery": {"updated": 0, "routes": 0}})
        self.assertEqual(preview[2:4], ("POST", f"/gadget-products/{PRODUCT}/manifests/preview"))
        self.assertEqual(pushed[2:4], ("PUT", f"/gadget-products/{PRODUCT}/manifests/dev"))
        self.assertEqual(preview[4], pushed[4])
        self.assertEqual(pushed[4]["scenarios"], content["scenarios"])
        self.assertEqual(pushed[4]["systemPrompt"], "A lamp.")
        self.assertNotIn("product", pushed[4])

    def test_legacy_omission_and_explicit_clear_remain_distinct(self):
        manifest = {"minFirmware": "0", "systemPrompt": "", "commands": [], "events": [], "revision": 1}
        pulled, _ = self.run_cli(["manifest", "pull", PRODUCT], {"manifests": {"dev": [manifest]}})
        content = json.loads(pulled)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_text(json.dumps(content))
            self.assertNotIn("scenarios", impo.read_manifest(path)[1])
            content["scenarios"] = []
            path.write_text(json.dumps(content))
            self.assertEqual(impo.read_manifest(path)[1]["scenarios"], [])


if __name__ == "__main__":
    unittest.main()
