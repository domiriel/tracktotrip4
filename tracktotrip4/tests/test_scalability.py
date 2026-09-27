import random
import unittest
from unittest.mock import patch
from tracktotrip4 import Point, Segment
from tracktotrip4.similarity import segment_similarity, sort_segment_points
from tracktotrip4.learn_trip import learn_trip


def segment(coords):
    return Segment([Point(x, y, None) for x, y in coords])


class ScalabilityTests(unittest.TestCase):
    def test_learning_does_not_mutate_input(self):
        current = segment([(0, 0), (1, 1), (2, 2)])
        original = list(current.points)
        learn_trip(current, 1, [], lambda *args: 7, lambda *args: None, .1, .1)
        self.assertEqual(current.points, original)

    def test_reusable_index_and_empty_similarity(self):
        from tracktotrip4.similarity import SegmentIndex
        a = segment([(0, 0), (1, 1), (2, 2)])
        b = segment([(0, 0), (1, 1)])
        with SegmentIndex(a, .1) as prepared:
            self.assertEqual(segment_similarity(a, b, T=.1),
                             segment_similarity(a, b, T=.1, prepared=prepared))
        self.assertEqual(segment_similarity(segment([]), b, T=.1)[0], 0)
        self.assertEqual(segment_similarity(a, segment([]), T=.1), (0.0, []))

    def test_one_new_trip_index_per_learning_call(self):
        from tracktotrip4 import similarity
        current = segment([(0, 0), (1, 1)])
        candidates = [(i, segment([(0, 10+i), (1, 11+i)])) for i in range(10)]
        with patch.object(similarity.index, 'Index', wraps=similarity.index.Index) as factory:
            learn_trip(current, 1, candidates, lambda *a: 1, lambda *a: None, .01, .1)
        self.assertLessEqual(factory.call_count, 11)

    def test_indexed_merge_matches_legacy(self):
        from tracktotrip4.similarity import distance_tt_point, dot, normalize, line
        def legacy(a, b):
            mid, j = [a[0]], 0
            for i in range(len(a)-1):
                dist = distance_tt_point(a[i], a[i+1])
                for m in range(j, len(b)):
                    if dist > distance_tt_point(a[i], b[m]):
                        if dot(normalize(line(a[i].gen2arr(), a[i+1].gen2arr())), normalize(b[m].gen2arr())) > 0:
                            j = m+1
                            mid.append(b[m])
                            break
                mid.append(a[i+1])
            return mid
        rng = random.Random(7)
        for _ in range(50):
            a = segment([(rng.random(), rng.random()) for _ in range(15)]).points
            b = segment([(rng.random(), rng.random()) for _ in range(15)]).points
            self.assertEqual(sort_segment_points(a, b), legacy(a, b))

    def test_distant_merge_avoids_cross_product(self):
        from tracktotrip4 import similarity
        a = segment([(i, i) for i in range(100)]).points
        b = segment([(i+10000, i+10000) for i in range(100)]).points
        with patch.object(similarity, 'distance_tt_point', wraps=similarity.distance_tt_point) as distance:
            sort_segment_points(a, b)
        self.assertLess(distance.call_count, 300)

    def test_bounded_index_cache_closes_evictions(self):
        from tracktotrip4.similarity import SegmentIndexCache
        with SegmentIndexCache(max_points=4) as cache:
            a = segment([(0, 0), (1, 1), (2, 2)])
            b = segment([(3, 3), (4, 4), (5, 5)])
            first = cache.get(a, .1)
            self.assertIs(first, cache.get(a, .1))
            cache.get(b, .1)
            self.assertLessEqual(cache.points, 4)

    def test_learning_returns_best_and_last_tie_without_mutation(self):
        current = segment([(0, 0), (1, 1), (2, 2)])
        candidates = [(1, segment([(0, 0), (1, 1), (2, 2)])),
                      (2, segment([(0, 0), (1, 1), (2, 2)]))]
        before = [list(trip.points) for _, trip in candidates]
        updates = []
        result = learn_trip(current, 4, candidates, lambda *a: -1,
                            lambda *a: updates.append(a), .01, .1)
        self.assertEqual(result, 2)
        self.assertEqual([list(trip.points) for _, trip in candidates], before)

    def test_canonical_point_budget_reports_error_and_preserves_source(self):
        current = segment([(i*.01, (i%2)*.01) for i in range(100)])
        stored = []
        learn_trip(current, 1, [], lambda trip, identity: stored.append(trip),
                   lambda *a: None, .000001, .01, max_points=12)
        self.assertEqual(len(current.points), 100)
        self.assertLessEqual(len(stored[0].points), 12)
        self.assertGreater(stored[0].representation_error, 0)
        self.assertEqual(stored[0].points[0].gen2arr(), current.points[0].gen2arr())
        self.assertEqual(stored[0].points[-1].gen2arr(), current.points[-1].gen2arr())

    def test_pruning_matches_exhaustive_selection_for_partial_and_reversed_routes(self):
        rng = random.Random(81)
        for _ in range(25):
            current = segment([(i*.01, rng.random()*.005) for i in range(12)])
            candidates = [(i, segment([(j*.01, rng.random()*.008) for j in range(12)])) for i in range(6)]
            candidates += [(7, segment([p.gen2arr() for p in current.points[3:9]])),
                           (8, segment([p.gen2arr() for p in reversed(current.points)]))]
            scores = [(max(segment_similarity(current, candidate, T=.01)[0],
                           segment_similarity(candidate, current, T=.01)[0]), i)
                      for i, candidate in candidates]
            expected = max(scores)[1] if max(scores)[0] >= .7 else -1
            found = learn_trip(current, 1, candidates, lambda *a: -1, lambda *a: None,
                               .0001, .01, max_points=None)
            self.assertEqual(found, expected)
