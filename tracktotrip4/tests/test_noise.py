"""Spike removal and joining of recording pieces, on synthetic tracks."""
import unittest
from unittest.mock import patch

from tracktotrip4 import Segment, Track
from tracktotrip4 import noise
from tracktotrip4.noise import remove_spikes
from tracktotrip4.segment import remove_liers
from tracktotrip4.track import join_segments
from tracktotrip4.tests.test_stay_segmentation import Recorder, point, xy


def spike(rec, dx, dy, count=1):
    """Records the next `count` positions (dx, dy) m away from where we are."""
    for _ in range(count):
        rec.walk(1.4 * rec.dt, 0)
        x, y = xy(rec.points[-1])
        rec.points[-1] = point(x + dx, y + dy, rec.t)
    return rec


def recorder(dt=1, jitter=3.0):
    return Recorder(dt=dt, jitter=jitter)


def ids(points):
    return [id(p) for p in points]


class RemoveSpikesTests(unittest.TestCase):
    def assertDropped(self, before, after, dropped):
        self.assertEqual(ids(after), [i for i in ids(before) if i not in {id(p) for p in dropped}])

    def test_clean_walk_is_untouched(self):
        rec = recorder().walk(800, 0).walk(0, 400)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_single_point_spike_while_walking_is_dropped(self):
        rec = recorder().walk(300, 0)
        spike(rec, 0, 150)
        bad = rec.points[-1]
        rec.walk(300, 0)
        self.assertDropped(rec.points, remove_spikes(rec.points), [bad])

    def test_burst_of_three_points_is_dropped(self):
        rec = recorder().walk(300, 0)
        spike(rec, 120, 200, count=3)
        bad = rec.points[-3:]
        rec.walk(300, 0)
        self.assertDropped(rec.points, remove_spikes(rec.points), bad)

    def test_spike_with_sparse_sampling_is_dropped(self):
        # old loggers: a point every 10 s; 200 m away and back in 20 s
        rec = recorder(dt=10).walk(500, 0)
        spike(rec, -50, 200)
        bad = rec.points[-1]
        rec.walk(500, 0)
        self.assertDropped(rec.points, remove_spikes(rec.points), [bad])

    def test_spike_reached_after_a_gap_is_dropped(self):
        # nothing for 100 s, then a fix 450 m away that snaps back 10 s later
        rec = recorder(dt=10).walk(300, 0)
        x, y = xy(rec.points[-1])
        bad = [point(x, 450, rec.t + 100), point(x + 60, 440, rec.t + 110)]
        rec.t += 120
        rec.points.extend(bad)
        rec.walk(300, 0)
        self.assertDropped(rec.points, remove_spikes(rec.points), bad)

    def test_spike_left_after_a_gap_is_dropped(self):
        rec = recorder(dt=10).walk(300, 0)
        x, y = xy(rec.points[-1])
        bad = point(x, 450, rec.t + 10)
        rec.points.append(bad)
        rec.t += 110
        rec.walk(300, 0)
        self.assertDropped(rec.points, remove_spikes(rec.points), [bad])

    def test_sideways_blips_are_dropped_at_any_sampling_rate(self):
        # walking south; one or two points jump west, then back on course
        for dt in (1, 5, 10):
            for west in (40, 80, 150):
                for count in (1, 2):
                    with self.subTest(dt=dt, west=west, count=count):
                        points = [point(-west if 40 <= i < 40 + count else 0, -1.4 * dt * i, dt * i)
                                  for i in range(80)]
                        self.assertDropped(points, remove_spikes(points), points[40:40 + count])

    def test_small_sideways_wobble_is_left_to_smoothing(self):
        points = [point(-20 if i == 40 else 0, -14 * i, 10 * i) for i in range(80)]
        self.assertEqual(ids(remove_spikes(points)), ids(points))

    def test_turning_a_corner_is_kept(self):
        rec = recorder(dt=10).walk(0, -500).walk(-500, 0).walk(0, 500)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_pulling_away_round_a_corner_is_kept(self):
        # stopped, then a point every 10 s: 100 m east, then 100 m north
        points = [point(0, 0, 10 * i) for i in range(6)]
        points += [point(100, 0, 60), point(100, 100, 70), point(100, 200, 80), point(100, 300, 90)]
        self.assertEqual(ids(remove_spikes(points)), ids(points))

    def test_walking_into_a_side_street_and_back_is_kept(self):
        rec = recorder(dt=10).walk(0, -500).walk(-60, 0).walk(60, 0).walk(0, -500)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_spikes_at_the_start_and_end_are_dropped(self):
        rec = recorder().walk(400, 0)
        first = point(xy(rec.points[0])[0] - 30, 250, -1)
        last = point(xy(rec.points[-1])[0], -250, rec.t + 1)
        points = [first] + rec.points + [last]
        self.assertDropped(points, remove_spikes(points), [first, last])

    def test_recording_ending_on_a_bad_fix_loses_it(self):
        rec = recorder().walk(400, 0)
        x = xy(rec.points[-1])[0]
        bad = [point(x, -250, rec.t + 1), point(x + 5, -255, rec.t + 2)]
        points = rec.points + bad
        self.assertDropped(points, remove_spikes(points), bad)

    def test_jump_after_losing_signal_is_kept(self):
        # underground: resumes 2 km on, 3 minutes later, and goes on from there
        rec = recorder().walk(300, 0).gap(180, dx=2000).walk(300, 0)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_relocation_that_stays_is_kept(self):
        # a sudden 150 m jump that the next points confirm is where we are
        rec = recorder().walk(300, 0)
        rec.x += 150
        rec.walk(300, 0)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_fast_tight_turn_is_kept(self):
        # car at 20 m/s, a point every 5 s, round a loop of 60 m radius
        rec = recorder(dt=5).walk(1000, 0, speed=20)
        for dx, dy in ((60, 60), (-60, 60), (-60, -60), (60, -60)):
            rec.walk(dx, dy, speed=20)
        rec.walk(1000, 0, speed=20)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_pulling_away_and_braking_on_a_straight_road_is_kept(self):
        # a point every 10 s: pulling away from a stop along a straight road,
        # then braking to a stop (backwards, pulling away again)
        steps = [2, 1, 3, 5, 12, 38, 79, 120, 135, 147, 219, 213, 229, 217,
                 164, 160, 147, 91, 55, 12, 5, 3, 1, 2]
        x, points = 0, [point(0, 0, 0)]
        for k, step in enumerate(steps, 1):
            x += step
            points.append(point(x, 0, 10 * k))
        self.assertEqual(ids(remove_spikes(points)), ids(points))

    def test_standing_still_is_untouched(self):
        rec = recorder().stay(600, spread=15)
        self.assertEqual(ids(remove_spikes(rec.points)), ids(rec.points))

    def test_short_inputs(self):
        self.assertEqual(remove_spikes([]), [])
        rec = recorder().walk(5, 0)
        self.assertEqual(ids(remove_spikes(rec.points[:2])), ids(rec.points[:2]))

    def test_work_is_linear(self):
        rec = recorder()
        for k in range(50):
            rec.walk(200, 0)
            spike(rec, 0, 150, count=1 + k % 3)
        calls = []
        real = noise._metres
        with patch.object(noise, '_metres', side_effect=lambda *a: calls.append(1) or real(*a)):
            remove_spikes(rec.points)
        self.assertLessEqual(len(calls), 20 * len(rec.points))


class RemoveLiersTests(unittest.TestCase):
    def test_points_in_time_order_are_all_kept(self):
        rec = recorder().walk(10, 0)
        self.assertEqual(ids(remove_liers(rec.points)), ids(rec.points))


class JoinSegmentsTests(unittest.TestCase):
    def pieces(self, gap, dx):
        rec = recorder().walk(500, 0)
        cut = len(rec.points)
        rec.gap(gap, dx=dx).walk(500, 0)
        return Segment(rec.points[:cut]), Segment(rec.points[cut:])

    def test_pieces_a_few_seconds_and_metres_apart_are_joined(self):
        one, two = self.pieces(10, 5)
        joined = join_segments([two, one], max_gap=15, max_distance=30)
        self.assertEqual(len(joined), 1)
        self.assertEqual(ids(joined[0].points), ids(one.points) + ids(two.points))

    def test_pieces_further_apart_in_time_stay_apart(self):
        self.assertEqual(len(join_segments(list(self.pieces(60, 5)), max_gap=15, max_distance=30)), 2)

    def test_pieces_further_apart_in_space_stay_apart(self):
        self.assertEqual(len(join_segments(list(self.pieces(10, 200)), max_gap=15, max_distance=30)), 2)

    def test_to_trip_joins_pieces_into_one_trip(self):
        one, two = self.pieces(10, 5)
        track = Track('t', [one, two])
        track.to_trip(smooth=False, smooth_strategy='inverse', smooth_noise=1000,
                      seg=True, seg_stay_radius=50, seg_stay_min_time=300, seg_max_gap=1800,
                      simplify=False, simplify_max_dist_error=2, simplify_max_speed_error=1)
        self.assertEqual(len(track.segments), 1)

    def test_to_trip_removes_spikes(self):
        rec = recorder().walk(300, 0)
        spike(rec, 0, 150)
        rec.walk(300, 0)
        track = Track('t', [Segment(list(rec.points))])
        track.to_trip(smooth=False, smooth_strategy='inverse', smooth_noise=1000,
                      seg=False, seg_stay_radius=50, seg_stay_min_time=300, seg_max_gap=1800,
                      simplify=False, simplify_max_dist_error=2, simplify_max_speed_error=1)
        self.assertEqual(len(track.segments[0].points), len(rec.points) - 1)


if __name__ == '__main__':
    unittest.main()
