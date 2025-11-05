from tracktotrip4 import learn_trip, Track, Segment, Point
from tracktotrip4.utils import estimate_meters_to_deg
from datetime import datetime, timedelta
import unittest

#TODO remake tests (these don't work)
class TestLearnTrip(unittest.TestCase):
    def setUp(self):
        Aps = [[0.5, 0.5], [1, 1.5], [2, 2.5], [3.5, 3.5], [5.2, 4.5], [7.5, 6.5], [7.9, 8]]
        Bps = [[0.6, 0.5], [1.05, 1.45], [2.1, 2.4], [2.8, 4], [3.5, 5.5], [5, 5.7], [7.8, 5.7], [8.1, 6.5], [8.1, 8]]
        
        time = datetime.now()
        dt = timedelta(1000)

        def pt_arr_to_track(pts):
            seg = Segment(list(map(lambda p: Point(p[0], p[1], time + dt), pts)))
            return Track(name="track", segments=[seg])

        self.trackA = pt_arr_to_track(Aps)
        self.trackA.to_trip(
            smooth=True,
            smooth_strategy="inverse",
            smooth_noise=1000,
            seg=True,
            seg_eps=0.01,
            seg_min_time=60,
            simplify=True,
            simplify_max_dist_error=2,
            simplify_max_speed_error=1
        )

        self.trackB = pt_arr_to_track(Bps)
        self.trackB.to_trip(
            smooth=True,
            smooth_strategy="inverse",
            smooth_noise=1000,
            seg=True,
            seg_eps=0.01,
            seg_min_time=60,
            simplify=True,
            simplify_max_dist_error=2,
            simplify_max_speed_error=1
        )

    def fail(self):
        self.assertTrue(False)


    def test_empty_list(self):
        def expected():
            self.assertTrue(True)

        for trip in self.trackA.segments:
            learn_trip.learn_trip(trip, None, [], lambda x,y: expected(), lambda x,y,z: self.fail(), 1.5e-05, estimate_meters_to_deg(20))

    def test_exact_matching_track(self):
        def expected():
            self.assertTrue(True)

        canonical =  [(i, s) for i, s in enumerate(self.trackA.copy().segments)]
        for trip in self.trackA.segments:
            learn_trip.learn_trip(trip, None, canonical, lambda x,y: self.fail(), lambda x,y,z: expected(), 1.5e-05, estimate_meters_to_deg(20))

    def test_matching_track(self):
        def expected():
            self.assertTrue(True)
        
        canonical =  [(i, s) for i, s in enumerate(self.trackB.copy().segments)]
        for trip in self.trackA.segments:
            learn_trip.learn_trip(trip, None, canonical, lambda x,y: expected(), lambda x,y,z: self.fail(), 1.5e-05, estimate_meters_to_deg(20))

if __name__ == '__main__':
    unittest.main()
