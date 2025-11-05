import gpxpy
import unittest
from tracktotrip4 import Point, Segment
from datetime import datetime, timedelta

def loadFile(name):
    return gpxpy.parse(open(name, 'r'))

class TestSegment(unittest.TestCase):
    def test_creation(self):
        s1 = Segment([])
        s2 = Segment([Point(0, 0, None)])

        self.assertEqual(len(s1.points), 0)
        self.assertEqual(len(s1.transportation_modes), 0)
        self.assertEqual(s1.location_from, None)
        self.assertEqual(s1.location_to, None)

        self.assertEqual(len(s2.points), 1)
        self.assertEqual(len(s2.transportation_modes), 0)
        self.assertEqual(s2.location_from, None)
        self.assertEqual(s2.location_to, None)

    def test_to_json(self):
        time = datetime.now()
        dt = timedelta(1000)

        s = Segment([Point(0, 0, time), Point(0, 1, time + dt), Point(0, 2, time + dt)])

        json = s.to_json()
        self.assertTrue('points' in json)
        self.assertTrue('transportationModes' in json)
        self.assertTrue('locationFrom' in json)
        self.assertTrue('locationTo' in json)

if __name__ == '__main__':
    unittest.main()
