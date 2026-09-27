"""
Removal of GPS spikes: points that jump away and come straight back
"""
import math
from collections import deque
from statistics import median

from .spatiotemporal_segmentation import M_PER_DEG, _metres

#: Longest run of consecutive bad points taken as one spike.
SPIKE_POINTS = 3

#: A jump is suspicious when it needs this many times the recent speed...
SPEED_FACTOR = 3.0

#: ...and at least this speed (m/s), so standing still doesn't make every
#: GPS wobble suspicious.
MIN_SPIKE_SPEED = 5.0

#: Recent steps whose median speed is the reference.
RECENT_STEPS = 5

#: A blip (points off the line of travel that come straight back) is a spike
#: when going through it is this many times longer than going straight...
DETOUR_RATIO = 2.0

#: ...and would need this many times the recent speed. A real side trip
#: takes the time it takes to walk it.
DETOUR_SPEED_FACTOR = 2.0


def _distance(a, b):
    return _metres(a.lat, a.lon, b.lat, b.lon)


def _off_path(point, a, b):
    """ Meters from `point` to the straight line between `a` and `b` """
    kx = math.cos(math.radians(a.lat)) * M_PER_DEG
    px, py = (point.lon - a.lon) * kx, (point.lat - a.lat) * M_PER_DEG
    bx, by = (b.lon - a.lon) * kx, (b.lat - a.lat) * M_PER_DEG
    length2 = bx * bx + by * by
    t = 0.0 if length2 == 0 else max(0.0, min(1.0, (px * bx + py * by) / length2))
    return math.hypot(px - t * bx, py - t * by)


def _is_spike(run, before, after, min_distance):
    """ Whether the points of `run` all stand out from the line between the
    points before and after them: a detour, not a stretch of the way """
    return all(_off_path(p, before, after) >= min_distance for p in run)


def _seconds(a, b):
    """ Time between two points, at least a second (loggers round times) """
    return max(1.0, abs((b.time - a.time).total_seconds()))


def _forward(points, min_distance):
    """ One pass in the order given: drops spikes in the middle and at the end """
    n = len(points)
    first_steps = [_distance(a, b) / _seconds(a, b)
                   for a, b in zip(points[:RECENT_STEPS], points[1:RECENT_STEPS + 1])]
    recent = deque([median(first_steps)], maxlen=RECENT_STEPS)

    def plausible(a, b, limit):
        distance = _distance(a, b)
        return distance < min_distance or distance / _seconds(a, b) <= limit

    kept = [points[0]]
    i = 1
    while i < n:
        anchor, point = kept[-1], points[i]
        blip = _blip(kept, point, median(recent), min_distance)
        if blip:
            del kept[-blip:]
            continue
        limit = max(SPEED_FACTOR * median(recent), MIN_SPIKE_SPEED)
        if plausible(anchor, point, limit):
            recent.append(_distance(anchor, point) / _seconds(anchor, point))
            kept.append(point)
            i += 1
            continue

        # A jump. A spike if, within a few points, the track is back where
        # plausible from before the jump, coming back as suddenly as it left
        back = None
        for j in range(i + 1, min(n, i + 1 + SPIKE_POINTS)):
            if plausible(anchor, points[j], limit):
                if not plausible(points[j - 1], points[j], limit) and \
                        _is_spike(points[i:j], anchor, points[j], min_distance):
                    back = j
                break
        if back is not None:
            i = back
        elif n - i <= SPIKE_POINTS and \
                all(_distance(point, p) < min_distance for p in points[i + 1:]):
            break           # the recording ends on a jump to one spot
        else:
            recent.append(_distance(anchor, point) / _seconds(anchor, point))
            kept.append(point)  # it stays there: a real relocation (lost signal)
            i += 1
    return kept


def _blip(kept, point, speed, min_distance):
    """ How many of the last points kept (0 if none) form a blip that `point`
    comes back from: they all stand out from the line between the point
    before them and `point`, and going through them is a detour much longer,
    and much faster, than the track goes. Catches spikes too slow to look
    like jumps: with sparse sampling, or reached or left across a gap """
    for count in range(1, min(SPIKE_POINTS, len(kept) - 1) + 1):
        base, run = kept[-1 - count], kept[-count:]
        if not _is_spike(run, base, point, min_distance):
            continue
        via = [base] + run + [point]
        detour = sum(_distance(a, b) for a, b in zip(via, via[1:]))
        if detour >= DETOUR_RATIO * _distance(base, point) and \
                detour / _seconds(base, point) >= DETOUR_SPEED_FACTOR * speed:
            return count
    return 0


def remove_spikes(points, min_distance=30):
    """ Drops spikes: up to `SPIKE_POINTS` consecutive points that jump at
    least `min_distance` meters off the way and come back, far faster than
    the track was moving, or as a sudden sideways blip (see `_blip`). A jump that the following points confirm (a
    fix recovered after losing signal) is kept. Runs in linear time

    Args:
        points (:obj:`list` of :obj:`Point`): time ordered points
        min_distance (float): meters; smaller jumps are left to smoothing
    Returns:
        :obj:`list` of :obj:`Point`
    """
    if len(points) < 3:
        return list(points)
    # a spike at the start is one at the end when going backwards
    return list(reversed(_forward(list(reversed(_forward(points, min_distance))), min_distance)))
