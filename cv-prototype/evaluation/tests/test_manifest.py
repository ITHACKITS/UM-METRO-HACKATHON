import json
import unittest
from pathlib import Path

from jagapadi_eval.manifest import (
    ManifestError,
    audit_manifest,
    canonical_manifest_hash,
    load_manifest,
    validate_manifest,
)


EXAMPLE = Path(__file__).parents[1] / "examples" / "manifest.synthetic.json"


class ManifestTests(unittest.TestCase):
    def test_synthetic_example_is_valid_and_auditable(self) -> None:
        manifest = load_manifest(EXAMPLE)
        result = audit_manifest(manifest)
        self.assertTrue(result["passed"])
        self.assertEqual(result["record_count"], 4)
        self.assertEqual(len(canonical_manifest_hash(manifest)), 64)

    def test_rejects_group_leakage_in_audit(self) -> None:
        manifest = load_manifest(EXAMPLE)
        manifest["records"][1]["group_id"] = manifest["records"][0]["group_id"]
        result = audit_manifest(manifest)
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["group_leakage"]), 1)

    def test_rejects_duplicate_content(self) -> None:
        manifest = load_manifest(EXAMPLE)
        manifest["records"][1]["sha256"] = manifest["records"][0]["sha256"]
        with self.assertRaisesRegex(ManifestError, "exact duplicate"):
            validate_manifest(manifest)

    def test_local_record_requires_off_git_consent(self) -> None:
        manifest = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        record = manifest["records"][0]
        record["source"]["kind"] = "local"
        with self.assertRaisesRegex(ManifestError, "consent"):
            validate_manifest(manifest)

    def test_rejects_incorrect_declared_manifest_hash(self) -> None:
        manifest = load_manifest(EXAMPLE)
        manifest["manifest_sha256"] = "0" * 64
        with self.assertRaisesRegex(ManifestError, "does not match"):
            validate_manifest(manifest)


if __name__ == "__main__":
    unittest.main()

