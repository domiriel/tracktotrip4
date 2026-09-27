"""Stay-based segmentation, on synthetic tracks (metres around an arbitrary origin)."""
import math
import random
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

from tracktotrip4 import Point, Segment, Track
from tracktotrip4 import spatiotemporal_segmentation as segmentation
from tracktotrip4.spatiotemporal_segmentation import stay_segmentation

ORIGIN_LAT, ORIGIN_LON = 45.0, 10.0
M_PER_DEG = 111195.0
T0 = datetime(2020, 1, 1, 8, 0, 0)

RADIUS = 30
MIN_TIME = 300
MAX_GAP = 1800


def point(x, y, t):
    """Point x metres east and y metres north of the origin, t seconds after T0."""
    lat = ORIGIN_LAT + y / M_PER_DEG
    lon = ORIGIN_LON + x / (M_PER_DEG * math.cos(math.radians(ORIGIN_LAT)))
    return Point(lat, lon, T0 + timedelta(seconds=t))


def xy(p):
    return ((p.lon - ORIGIN_LON) * M_PER_DEG * math.cos(math.radians(ORIGIN_LAT)),
            (p.lat - ORIGIN_LAT) * M_PER_DEG)


class Recorder:
    """Builds a track as a person moves: walks, stays with GPS jitter, gaps."""

    def __init__(self, x=0.0, y=0.0, dt=1, jitter=5.0, seed=1):
        self.x, self.y, self.t, self.dt = x, y, 0, dt
        self.jitter = jitter
        self.rand = random.Random(seed)
        self.points = []

    def _record(self, spread):
        self.points.append(point(self.x + self.rand.uniform(-spread, spread),
                                 self.y + self.rand.uniform(-spread, spread), self.t))

    def walk(self, dx, dy, speed=1.4):
        steps = max(1, int(math.hypot(dx, dy) / (speed * self.dt)))
        sx, sy = dx / steps, dy / steps
        for _ in range(steps):
            self.x += sx
            self.y += sy
            self.t += self.dt
            self._record(self.jitter)
        return self

    def stay(self, seconds, spread=12.0):
        for _ in range(int(seconds / self.dt)):
            self.t += self.dt
            self._record(spread)
        return self

    def gap(self, seconds, dx=0.0, dy=0.0):
        """Nothing recorded for `seconds`, while moving (dx, dy) metres."""
        self.t += seconds
        self.x += dx
        self.y += dy
        self._record(self.jitter)
        return self


def split(points, radius=RADIUS, min_time=MIN_TIME, max_gap=MAX_GAP):
    return stay_segmentation(points, radius, min_time, max_gap)


def seconds(p):
    return (p.time - T0).total_seconds()


class StaySegmentationTests(unittest.TestCase):
    def test_plain_walk_is_one_trip(self):
        rec = Recorder().walk(1000, 0)
        trips = split(rec.points)
        self.assertEqual(len(trips), 1)
        self.assertEqual(len(trips[0]), len(rec.points))

    def test_stay_with_continuous_logging_splits(self):
        rec = Recorder().walk(800, 0)
        arrive = rec.t
        rec.stay(600)
        leave = rec.t
        rec.walk(0, 800)
        trips = split(rec.points)
        self.assertEqual(len(trips), 2)
        self.assertLessEqual(seconds(trips[0][-1]), arrive + 60)
        self.assertGreaterEqual(seconds(trips[1][0]), leave - 60)

    def test_stationary_start_and_end_are_trimmed(self):
        rec = Recorder().stay(900)
        leave = rec.t
        rec.walk(1000, 0)
        arrive = rec.t
        rec.stay(900)
        trips = split(rec.points)
        self.assertEqual(len(trips), 1)
        self.assertGreaterEqual(seconds(trips[0][0]), leave - 60)
        self.assertLessEqual(seconds(trips[0][-1]), arrive + 60)

    def test_short_stationary_gap_is_joined(self):
        rec = Recorder().walk(500, 0).gap(180).walk(500, 0)
        self.assertEqual(len(split(rec.points)), 1)

    def test_long_stationary_gap_splits(self):
        rec = Recorder().walk(500, 0).gap(900).walk(500, 0)
        trips = split(rec.points)
        self.assertEqual(len(trips), 2)

    def test_gap_while_moving_stays_one_trip(self):
        # signal lost underground: resumes 5 km on, 10 minutes later
        rec = Recorder().walk(500, 0).gap(600, dx=5000).walk(500, 0)
        self.assertEqual(len(split(rec.points)), 1)

    def test_slow_gap_ending_elsewhere_splits(self):
        # fix lost inside a shop; picked up again 200 m away 20 minutes later
        rec = Recorder().walk(500, 0).gap(1200, dx=200).walk(500, 0)
        self.assertEqual(len(split(rec.points)), 2)

    def test_very_long_gap_while_moving_splits(self):
        rec = Recorder().walk(500, 0).gap(3600, dx=5000).walk(500, 0)
        self.assertEqual(len(split(rec.points)), 2)

    def test_walk_between_places_40m_apart_is_a_trip(self):
        rec = Recorder(jitter=2).stay(600, spread=5)
        rec.walk(40, 0)
        rec.stay(600, spread=5)
        trips = split(rec.points)
        self.assertEqual(len(trips), 1)
        self.assertLess(xy(trips[0][0])[0], 20)
        self.assertGreater(xy(trips[0][-1])[0], 20)

    def test_excursion_returning_to_the_same_place_is_not_a_trip(self):
        rec = Recorder(jitter=2).stay(600, spread=5)
        rec.walk(45, 0).walk(-45, 0)
        rec.stay(600, spread=5)
        self.assertEqual(split(rec.points), [])

    def test_never_leaving_gives_no_trip(self):
        rec = Recorder().stay(3600, spread=25)
        self.assertEqual(split(rec.points), [])

    def test_trips_are_consecutive_points_in_order(self):
        rec = Recorder().walk(800, 0).stay(600).walk(0, 800)
        order = {id(p): i for i, p in enumerate(rec.points)}
        for trip in split(rec.points):
            indexes = [order[id(p)] for p in trip]
            self.assertEqual(indexes, list(range(indexes[0], indexes[-1] + 1)))

    def test_distance_work_is_linear(self):
        rec = Recorder(dt=1)
        for _ in range(20):
            rec.walk(700, 0).stay(400).walk(0, 300).stay(200, spread=25)
        calls = []
        real = segmentation._metres
        with patch.object(segmentation, '_metres', side_effect=lambda *a: calls.append(1) or real(*a)):
            split(rec.points)
        self.assertLessEqual(len(calls), 3 * len(rec.points))

    def test_empty_and_single_point(self):
        self.assertEqual(split([]), [])
        self.assertEqual(split([point(0, 0, 0)]), [])


class TrackSegmentTests(unittest.TestCase):
    def test_to_trip_uses_stay_segmentation(self):
        rec = Recorder().walk(800, 0).stay(600).walk(0, 800)
        track = Track('t', [Segment(rec.points)])
        track.to_trip(smooth=False, smooth_strategy='inverse', smooth_noise=1000,
                      seg=True, seg_stay_radius=RADIUS, seg_stay_min_time=MIN_TIME,
                      seg_max_gap=MAX_GAP, simplify=False,
                      simplify_max_dist_error=2, simplify_max_speed_error=1)
        self.assertEqual(len(track.segments), 2)


if __name__ == '__main__':
    unittest.main()
