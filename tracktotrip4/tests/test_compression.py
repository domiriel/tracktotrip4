"""Spatiotemporal simplification (spt)."""
import math
import unittest
from datetime import datetime, timedelta

from tracktotrip4 import Point
from tracktotrip4.compression import spt

T0 = datetime(2020, 1, 1, 8)


def zigzag(count, spread=0.0002):
    """A point a second, each off the line of the previous ones: every point
    is kept."""
    return [Point(38.7 + (spread if k % 2 else 0), -9.1 + k * 0.00002, T0 + timedelta(seconds=k))
            for k in range(count)]


class SptTests(unittest.TestCase):
    def test_straight_steady_line_keeps_its_ends(self):
        points = [Point(38.7, -9.1 + k * 0.00002, T0 + timedelta(seconds=k)) for k in range(50)]
        self.assertEqual(spt(points, 2.0, 1.0), [points[0], points[-1]])

    def test_short_inputs_are_kept(self):
        points = zigzag(2)
        self.assertEqual(spt(points, 2.0, 1.0), points)

    def test_long_detailed_recording_keeps_every_needed_point(self):
        # a phone logging every second for hours keeps tens of thousands of
        # points: no limit on how many
        points = zigzag(30000)
        self.assertEqual([id(p) for p in spt(points, 2.0, 1.0)], [id(p) for p in points])


if __name__ == '__main__':
    unittest.main()
