import unittest
from pathlib import Path

from jagapadi_eval.manifest import load_manifest
from jagapadi_eval.report import build_pending_report


EXAMPLE = Path(__file__).parents[1] / "examples" / "manifest.synthetic.json"


class ReportTests(unittest.TestCase):
    def test_pending_report_does_not_invent_accuracy(self) -> None:
        report = build_pending_report(load_manifest(EXAMPLE))
        self.assertIn("no project accuracy claim", report)
        self.assertIn("not_testable", report)
        self.assertNotIn("94.77%", report)
        self.assertIn("not diagnoses", report)


if __name__ == "__main__":
    unittest.main()

