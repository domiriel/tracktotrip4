"""
Learns trips
"""
import numpy as np
from .similarity import segment_similarity, SegmentIndex
from contextlib import ExitStack
from copy import deepcopy

def complete_trip(canonical_trips, from_point, to_point, distance_thr, debug = False):
    """ Completes a trip based on set of canonical trips

    Args:
        canonical_trips (:obj:`list` of :obj:`Segment`)
        from_point (:obj:`Point`)
        to_point (:obj:`Point`)
    """
    result = []
    weights = []
    total_weights = 0.0
    # match points in lines
    for (_, trip, count) in canonical_trips:
        current_result = []
        from_index, from_closest = trip.closest_point_to(from_point, thr=distance_thr)
        to_index, to_closest = trip.closest_point_to(to_point, thr=distance_thr)

        if from_index != -1 and to_index != -1:
            trip_slice = trip.slice(from_index, to_index+1)
            if trip.points[from_index] != from_closest and from_point.distance(from_closest) < from_point.distance(trip_slice.points[0]):
                trip_slice.points[0] = from_closest
            if trip.points[to_index] != to_closest and to_point.distance(to_closest) < to_point.distance(trip_slice.points[-1]):
                trip_slice.points[-1] = to_closest

            result.append([[p.lat, p.lon] for p in trip_slice.points])
            weights.append(count)
            total_weights = total_weights + count


    aa = {
        'possibilities': result,
        'weights': list(np.array(weights) / total_weights)
    }

    if debug:
        print([len(r) for r in result])
        print(weights)

    return aa


def learn_trip(current, current_id, canonical_trips, insert_canonical, update_canonical,
               eps, distance_thr, debug=False, index_cache=None, stats=None, max_points=2048):
    """Select the best legacy match, preserving last-candidate tie breaking.

    index_cache optionally supplies get(segment, threshold) -> SegmentIndex and
    owns its returned indexes. Source segments are never mutated. Returns the
    canonical ID supplied by insert_canonical, or the matched existing ID.
    """
    stats = stats if stats is not None else {}
    stats.update(candidates=0, scored=0, pruned=0)
    best = None
    best_score = 0.7
    with ExitStack() as stack:
        current_index = stack.enter_context(SegmentIndex(current, distance_thr))
        for trip_id, trip in canonical_trips:
            stats['candidates'] += 1
            candidate_index = (index_cache.get(trip, distance_thr) if index_cache else
                               SegmentIndex(trip, distance_thr))
            try:
                upper = max(candidate_index.upper_bound(current), current_index.upper_bound(trip))
                if upper + 1e-12 < best_score:
                    stats['pruned'] += 1
                    continue
                score = max(segment_similarity(trip, current, T=distance_thr, prepared=candidate_index)[0],
                            segment_similarity(current, trip, T=distance_thr, prepared=current_index)[0])
                stats['scored'] += 1
                if score >= best_score:
                    best, best_score = (trip_id, trip), score
            finally:
                if index_cache is None:
                    candidate_index.close()
    if best is not None:
        trip_id, original = best
        trip = deepcopy(original)
        trip.merge_and_fit(current)
        trip.simplify(eps, 0, 0, topology_only=True)
        bound_representation(trip, max_points)
        stats["representation_error"] = trip.representation_error
        update_canonical(trip_id, trip, current_id)
        return trip_id
    trip = deepcopy(current)
    trip.simplify(eps, 0, 0, topology_only=True)
    bound_representation(trip, max_points)
    stats["representation_error"] = trip.representation_error
    return insert_canonical(trip, current_id)


def bound_representation(trip, max_points):
    """Bound derived geometry only; return maximum planar error in degrees.

    Split the remaining edge with greatest deviation until the budget is spent.
    Original per-trip geometry remains untouched and can rebuild this projection.
    """
    import heapq
    from .similarity import distance_to_line
    if max_points is None or len(trip.points) <= max_points:
        trip.representation_error = 0.0
        return
    if max_points < 2:
        raise ValueError('Canonical point budget must be at least two')
    points = trip.points
    heap = []
    def add(lo, hi):
        if hi-lo <= 1:
            return
        a, b = points[lo].gen2arr(), points[hi].gen2arr()
        error, split = max((distance_to_line(a, b, points[i].gen2arr()), i)
                           for i in range(lo+1, hi))
        heapq.heappush(heap, (-error, lo, hi, split))
    kept = {0, len(points)-1}
    add(0, len(points)-1)
    while heap and len(kept) < max_points:
        _, lo, hi, split = heapq.heappop(heap)
        kept.add(split)
        add(lo, split)
        add(split, hi)
    trip.representation_error = -heap[0][0] if heap else 0.0
    trip.points = [points[i] for i in sorted(kept)]
