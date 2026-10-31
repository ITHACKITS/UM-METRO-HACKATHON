import importlib.util
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).with_name("check_staged_boundary.py")
SPEC = importlib.util.spec_from_file_location("boundary", MODULE_PATH)
assert SPEC and SPEC.loader
BOUNDARY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(BOUNDARY)


class BoundaryTests(unittest.TestCase):
    def test_accepts_approved_integrated_application_paths(self) -> None:
        self.assertEqual(
            BOUNDARY.invalid_staged_paths(
                [
                    "cv-prototype/evaluation/report.py",
                    "frontend/src/sigap/Sigap.tsx",
                    "backend/app/sigap/router.py",
                    "README.id.md",
                ]
            ),
            [],
        )

    def test_rejects_context_private_data_and_model_artifacts(self) -> None:
        self.assertEqual(
            BOUNDARY.invalid_staged_paths(
                [
                    "CONTEXT.md",
                    "cv-prototype/.models/pest/model.onnx",
                    "cv-prototype/private-data/leaf.jpg",
                    "models/disease/model.safetensors",
                ]
            ),
            [
                "CONTEXT.md",
                "cv-prototype/.models/pest/model.onnx",
                "cv-prototype/private-data/leaf.jpg",
                "models/disease/model.safetensors",
            ],
        )


if __name__ == "__main__":
    unittest.main()

