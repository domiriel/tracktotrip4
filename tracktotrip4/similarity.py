"""
Similarity functions
"""

import math

import numpy as np
from rtree import index

#pylint: disable=invalid-name

def dot(p1, p2, debug = False):
    """Dot product between two points

    Args:
        p1 ([float, float]): x and y coordinates
        p2 ([float, float]): x and y coordinates
    Returns:
        float
    """
    return p1[0] * p2[0] + p1[1] * p2[1]

def normalize(p, debug = False):
    """Normalizes a point/vector

    Args:
        p ([float, float]): x and y coordinates
    Returns:
        float
    """
    l = math.sqrt(p[0]**2 + p[1]**2)
    return [0.0, 0.0] if l == 0 else [p[0]/l, p[1]/l]

def angle(p1, p2, debug = False):
    """Angle between two points

    Args:
        p1 ([float, float]): x and y coordinates
        p2 ([float, float]): x and y coordinates
    Returns:
        float
    """
    return dot(p1, p2, debug)

def angle_similarity(l1, l2, debug = False):
    """Computes the similarity between two lines, based
    on their angles

    Args:
        l1 ([float, float]): x and y coordinates
        l2 ([float, float]): x and y coordinates
    Returns:
        float
    """
    return angle(l1, l2, debug)

def line(p1, p2, debug = False):
    """Creates a line from two points

    From http://stackoverflow.com/a/20679579

    Args:
        p1 ([float, float]): x and y coordinates
        p2 ([float, float]): x and y coordinates
    Returns:
        (float, float, float): x, y and _
    """
    A = (p1[1] - p2[1])
    B = (p2[0] - p1[0])
    C = (p1[0]*p2[1] - p2[0]*p1[1])
    return A, B, -C

def intersection(L1, L2, debug = False):
    """Intersects two line segments

    Args:
        L1 ([float, float]): x and y coordinates
        L2 ([float, float]): x and y coordinates
    Returns:
        bool: if they intersect
        (float, float): x and y of intersection, if they do
    """
    D = L1[0] * L2[1] - L1[1] * L2[0]
    Dx = L1[2] * L2[1] - L1[1] * L2[2]
    Dy = L1[0] * L2[2] - L1[2] * L2[0]
    if D != 0:
        x = Dx / D
        y = Dy / D
        return x, y
    else:
        return False

def distance(a, b, debug = False):
    """Distance between two points

    Args:
        a ([float, float]): x and y coordinates
        b ([float, float]): x and y coordinates
    Returns:
        float
    """
    return math.sqrt((b[0]-a[0])**2 + (b[1]-a[1])**2)

def distance_tt_point(a, b, debug = False):
    """ Euclidean distance between two (tracktotrip) points

    Args:
        a (:obj:`Point`)
        b (:obj:`Point`)
    Returns:
        float
    """
    return math.sqrt((b.lat-a.lat)**2 + (b.lon-a.lon)**2)

def closest_point(a, b, p, debug = False):
    """Finds closest point in a line segment

    Args:
        a ([float, float]): x and y coordinates. Line start
        b ([float, float]): x and y coordinates. Line end
        p ([float, float]): x and y coordinates. Point to find in the segment
    Returns:
        (float, float): x and y coordinates of the closest point
    """
    ap = [p[0]-a[0], p[1]-a[1]]
    ab = [b[0]-a[0], b[1]-a[1]]
    mag = float(ab[0]**2 + ab[1]**2)
    proj = dot(ap, ab, debug)
    if mag ==0 :
        dist = 0
    else:
        dist = proj / mag
    if dist < 0:
        return [a[0], a[1]]
    elif dist > 1:
        return [b[0], b[1]]
    else:
        return [a[0] + ab[0] * dist, a[1] + ab[1] * dist]

def distance_to_line(a, b, p, debug = False):
    """Closest distance between a line segment and a point

    Args:
        a ([float, float]): x and y coordinates. Line start
        b ([float, float]): x and y coordinates. Line end
        p ([float, float]): x and y coordinates. Point to compute the distance
    Returns:
        float
    """
    return distance(closest_point(a, b, p, debug), p, debug)

CLOSE_DISTANCE_THRESHOLD = 1.0
def distance_similarity(a, b, p, T=CLOSE_DISTANCE_THRESHOLD, debug = False):
    """Computes the distance similarity between a line segment
    and a point

    Args:
        a ([float, float]): x and y coordinates. Line start
        b ([float, float]): x and y coordinates. Line end
        p ([float, float]): x and y coordinates. Point to compute the distance
    Returns:
        float: between 0 and 1. Where 1 is very similar and 0 is completely different
    """
    d = distance_to_line(a, b, p, debug)
    r = (-1/float(T)) * abs(d) + 1

    return r if r > 0 else 0

def line_distance_similarity(p1a, p1b, p2a, p2b, T=CLOSE_DISTANCE_THRESHOLD, debug = False):
    """Line distance similarity between two line segments

    Args:
        p1a ([float, float]): x and y coordinates. Line A start
        p1b ([float, float]): x and y coordinates. Line A end
        p2a ([float, float]): x and y coordinates. Line B start
        p2b ([float, float]): x and y coordinates. Line B end
    Returns:
        float: between 0 and 1. Where 1 is very similar and 0 is completely different
    """
    d1 = distance_similarity(p1a, p1b, p2a, T=T, debug=debug)
    d2 = distance_similarity(p1a, p1b, p2b, T=T, debug=debug)
    return abs(d1 + d2) * 0.5

def line_similarity(p1a, p1b, p2a, p2b, T=CLOSE_DISTANCE_THRESHOLD, debug = False):
    """Similarity between two lines

    Args:
        p1a ([float, float]): x and y coordinates. Line A start
        p1b ([float, float]): x and y coordinates. Line A end
        p2a ([float, float]): x and y coordinates. Line B start
        p2b ([float, float]): x and y coordinates. Line B end
    Returns:
        float: between 0 and 1. Where 1 is very similar and 0 is completely different
    """
    d = line_distance_similarity(p1a, p1b, p2a, p2b, T=T, debug=debug)
    a = abs(angle_similarity(normalize(line(p1a, p1b, debug), debug), normalize(line(p2a, p2b, debug), debug), debug))
    return d * a

def bounding_box_from(points, i, i1, thr, debug = False):
    """Creates bounding box for a line segment

    Args:
        points (:obj:`list` of :obj:`Point`)
        i (int): Line segment start, index in points array
        i1 (int): Line segment end, index in points array
    Returns:
        Rect(float, float, float, float): with bounding box min x, min y, max x and max y
    """
    pi = points[i]
    pi1 = points[i1]

    min_lat = min(pi.lat, pi1.lat)
    min_lon = min(pi.lon, pi1.lon)
    max_lat = max(pi.lat, pi1.lat)
    max_lon = max(pi.lon, pi1.lon)

    return min_lat-thr, min_lon-thr, max_lat+thr, max_lon+thr

class SegmentIndex:
    """Reusable, explicitly owned index of a segment's immutable coordinates."""
    def __init__(self, segment, threshold):
        self.threshold = threshold
        self.coords = tuple(tuple(p.gen2arr()) for p in segment.points)
        self.tree = index.Index()
        for i in range(len(self.coords)-1):
            self.tree.insert(i, bounding_box_from(segment.points, i, i+1, threshold))

    def close(self):
        self.tree.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def upper_bound(self, other):
        # Each line contributes at most 1. A disjoint expanded box contributes 0.
        # This is a conservative bound for the existing similarity, not a new
        # endpoint/length heuristic that could discard partial-route matches.
        count = len(other.points)-1
        if count <= 0:
            return 0.0
        hits = sum(self.tree.count(bounding_box_from(other.points, i, i+1, self.threshold)) > 0
                   for i in range(count))
        return hits / count


def segment_similarity(A, B, T=CLOSE_DISTANCE_THRESHOLD, debug=False, prepared=None):
    """Directional legacy score; optionally reuse an index for unchanged A."""
    if prepared is None:
        with SegmentIndex(A, T) as owned:
            return segment_similarity(A, B, T, debug, owned)
    if prepared.threshold != T:
        raise ValueError("Index threshold does not match similarity threshold")
    parts = []
    for i in range(len(B.points)-1):
        ti, ti1 = B.points[i].gen2arr(), B.points[i+1].gen2arr()
        best = 0.0
        for candidate in prepared.tree.intersection(bounding_box_from(B.points, i, i+1, T)):
            best = max(best, line_similarity(ti, ti1, prepared.coords[candidate],
                                             prepared.coords[candidate+1], T, debug))
        parts.append(best)
    return (float(np.mean(parts)) if parts else 0.0), parts

def sort_segment_points(Aps, Bps, debug = False):
    """Takes two line segments and sorts all their points,
    so that they form a continuous path

    Args:
        Aps: Array of tracktotrip.Point
        Bps: Array of tracktotrip.Point
    Returns:
        Array with points ordered
    """
    if not Aps:
        return list(Bps)
    # Query only points within the current edge's search radius, then retain
    # the original B ordering and exact distance/direction acceptance rules.
    tree = index.Index()
    try:
        for i, point in enumerate(Bps):
            tree.insert(i, (point.lat, point.lon, point.lat, point.lon))
        mid, j = [Aps[0]], 0
        for i in range(len(Aps)-1):
            point = Aps[i]
            dist = distance_tt_point(point, Aps[i+1], debug)
            candidates = sorted(tree.intersection((point.lat-dist, point.lon-dist,
                                                   point.lat+dist, point.lon+dist)))
            for m in candidates:
                if m < j:
                    continue
                if dist > distance_tt_point(point, Bps[m], debug):
                    direction = dot(normalize(line(point.gen2arr(), Aps[i+1].gen2arr(), debug), debug),
                                    normalize(Bps[m].gen2arr(), debug), debug)
                    if direction > 0:
                        j = m+1
                        mid.append(Bps[m])
                        break
            mid.append(Aps[i+1])
        return mid
    finally:
        tree.close()


class SegmentIndexCache:
    """LRU bounded by both coordinates and entries; coordinates are revision keys."""
    def __init__(self, max_points=100000, max_entries=512):
        from collections import OrderedDict
        self.entries = OrderedDict()
        self.max_points = max_points
        self.max_entries = max_entries
        self.points = 0
        self.oversized = None

    def get(self, segment, threshold):
        key = (threshold, tuple((p.lat, p.lon) for p in segment.points))
        if key in self.entries:
            self.entries.move_to_end(key)
            return self.entries[key]
        result = SegmentIndex(segment, threshold)
        size = len(segment.points)
        if size > self.max_points:
            # One borrowed oversized index, replaced on the next miss.
            if self.oversized:
                self.oversized.close()
            self.oversized = result
            return result
        self.entries[key] = result
        self.points += size
        while self.points > self.max_points or len(self.entries) > self.max_entries:
            old_key, old = self.entries.popitem(last=False)
            self.points -= len(old_key[1])
            old.close()
        return result

    def close(self):
        for entry in self.entries.values():
            entry.close()
        self.entries.clear()
        self.points = 0
        if self.oversized:
            self.oversized.close()
            self.oversized = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
