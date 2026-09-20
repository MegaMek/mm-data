"""Behavioral checks for the offline terrain normal-map preparation."""
import unittest

import numpy as np
from PIL import Image

from prepare_board_normals import FLAT, faceted


class BoardNormalsTest(unittest.TestCase):
    def test_uniform_hex_is_flat_and_transparent_rgb_never_becomes_relief(self):
        pixels = np.full((72, 84, 4), (100, 120, 80, 255), dtype=np.uint8)
        pixels[:20, :20, 3] = 0
        before = np.array(faceted(Image.fromarray(pixels), 12))
        self.assertTrue(np.all(before[:, :, :3] == FLAT))
        pixels[:20, :20, :3] = (255, 0, 255)
        after = np.array(faceted(Image.fromarray(pixels), 12))
        np.testing.assert_array_equal(before, after)
        np.testing.assert_array_equal(after[:, :, 3], pixels[:, :, 3])

    def test_slope_faces_downhill_in_both_image_axes(self):
        y, x = np.indices((32, 32))
        pixels = np.zeros((32, 32, 4), dtype=np.uint8)
        pixels[:, :, :3] = (4 * x + 2 * y)[:, :, None]
        pixels[:, :, 3] = 255
        normals = np.array(faceted(Image.fromarray(pixels), 12))[5:25, 5:25, :3]
        self.assertTrue(np.all(normals[:, :, 0] < normals[:, :, 1]))
        self.assertTrue(np.all(normals[:, :, 1] < 128))
        self.assertTrue(np.all(normals[:, :, 2] > 128))
        # An affine height field has the same direction across every triangular facet.
        self.assertLessEqual(np.ptp(normals.reshape(-1, 3).astype(int), axis=0).max(), 1)

    def test_concrete_remains_flat_even_when_its_paint_contains_contrast(self):
        pixels = np.random.default_rng(7).integers(0, 256, (72, 84, 4), dtype=np.uint8)
        normal = np.array(faceted(Image.fromarray(pixels), 0))
        self.assertTrue(np.all(normal[:, :, :3] == FLAT))
        np.testing.assert_array_equal(normal[:, :, 3], pixels[:, :, 3])


if __name__ == '__main__':
    unittest.main()
