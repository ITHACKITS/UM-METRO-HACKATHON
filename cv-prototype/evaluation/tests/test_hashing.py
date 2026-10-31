import tempfile
import unittest
from pathlib import Path

from PIL import Image

from jagapadi_eval.hashing import hamming_distance, hash_file, perceptual_hash


class HashingTests(unittest.TestCase):
    def test_content_and_perceptual_hashes_are_stable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "leaf.png"
            Image.new("RGB", (20, 20), (20, 100, 30)).save(path)
            self.assertEqual(hash_file(path), hash_file(path))
            self.assertEqual(len(hash_file(path)), 64)
            self.assertEqual(perceptual_hash(path), perceptual_hash(path))
            self.assertEqual(len(perceptual_hash(path)), 16)

    def test_hamming_distance(self) -> None:
        self.assertEqual(hamming_distance("0000", "0000"), 0)
        self.assertEqual(hamming_distance("0000", "ffff"), 16)
        with self.assertRaises(ValueError):
            hamming_distance("0", "00")


if __name__ == "__main__":
    unittest.main()

