"""
Segmentation of points into trips, at stays and at gaps in the recording
"""
import math

M_PER_DEG = 111195.0

#: Consecutive points outside a stay's radius needed to leave it; fewer are
#: GPS jitter and stay part of it.
LEAVE_POINTS = 3

#: Speed (m/s) across a recording gap below which the gap is taken as a stop
#: somewhere (e.g. indoors without a fix) rather than as travel without signal.
GAP_MOVING_SPEED = 0.5


def _metres(lat1, lon1, lat2, lon2):
    """ Equirectangular distance, in meters: exact enough at stay scale """
    x = (lon2 - lon1) * math.cos(math.radians((lat1 + lat2) / 2.0))
    return math.hypot(x, lat2 - lat1) * M_PER_DEG


def _seconds(point, previous):
    return (point.time - previous.time).total_seconds()


def _find_stays(points, stay_radius, stay_min_time, max_gap):
    """ Single pass over points: stays as [first, last, lat, lon] and the
        indexes that start a new trip after a gap (the previous point ends one)
    """
    stays = []
    breaks = []
    start = last_inside = 0
    count = 1
    lat, lon = points[0].lat, points[0].lon
    outside = 0

    for k in range(1, len(points)):
        point = points[k]
        dist = _metres(lat, lon, point.lat, point.lon)
        if dist <= stay_radius:
            outside = 0
            last_inside = k
            count += 1
            lat += (point.lat - lat) / count
            lon += (point.lon - lon) / count
            continue

        gap = _seconds(point, points[k - 1])
        stop_at_gap = gap > max_gap or (gap >= stay_min_time and _metres(
            points[k - 1].lat, points[k - 1].lon, point.lat, point.lon) < GAP_MOVING_SPEED * gap)
        outside += 1
        if not stop_at_gap and outside < LEAVE_POINTS:
            continue

        if _seconds(points[last_inside], points[start]) >= stay_min_time:
            stays.append([start, last_inside, lat, lon])
        if stop_at_gap:
            breaks.append(k)
        start = last_inside = k
        count = 1
        lat, lon = point.lat, point.lon
        outside = 0

    if _seconds(points[last_inside], points[start]) >= stay_min_time:
        stays.append([start, last_inside, lat, lon])
    return stays, breaks


def _merge_returns(stays, breaks, stay_radius):
    """ Consecutive stays at the same place are one stay: what was between them
        didn't go anywhere
    """
    merged = []
    b = 0
    for stay in stays:
        while b < len(breaks) and breaks[b] <= stay[0]:
            b += 1
        if merged:
            last = merged[-1]
            no_break = b == 0 or breaks[b - 1] <= last[1]
            if no_break and _metres(last[2], last[3], stay[2], stay[3]) <= stay_radius:
                last[1] = stay[1]
                continue
        merged.append(list(stay))
    return merged


def _core(points, stay, core_radius, trim_first, trim_last):
    """ First and last points of a stay close to its centre: the arrival and
        departure, without the approach and departure walks it absorbed. Only
        a side reached by moving is trimmed; otherwise the recording (or a gap)
        begins or ends in the stay itself
    """
    first, last, lat, lon = stay
    arrive, leave = first, last
    while trim_first and arrive < last and \
            _metres(lat, lon, points[arrive].lat, points[arrive].lon) > core_radius:
        arrive += 1
    while trim_last and leave > arrive and \
            _metres(lat, lon, points[leave].lat, points[leave].lon) > core_radius:
        leave -= 1
    return arrive, leave


def _goes_somewhere(points, first, last, stay_radius):
    origin = points[first]
    return any(_metres(origin.lat, origin.lon, p.lat, p.lon) > stay_radius
               for p in points[first + 1:last + 1])


def stay_segmentation(points, stay_radius, stay_min_time, max_gap, debug=False):
    """ Splits points into trips: the movement between stays

    A stay is a period of at least `stay_min_time` seconds during which the
    points remain within `stay_radius` meters of their centre, whether they
    were recorded (GPS left on: a "ball of wire") or not (a gap in the
    recording that resumes at the same place). Stays are not part of trips, so
    stationary stretches at the start or end of a recording are trimmed; a
    trip ends where a stay begins and the next trip starts where it ends.

    A recording gap resuming elsewhere splits too when it is longer than
    `max_gap` seconds, or when it is at least `stay_min_time` long and too
    slow to be travel without signal (then it is a stop that wasn't recorded).
    Shorter gaps are joined. A trip that never leaves `stay_radius` of its
    start is dropped.

    Runs in linear time in the number of points.

    Args:
        points (:obj:`list` of :obj:`Point`): time ordered points
        stay_radius (float): meters
        stay_min_time (float): seconds
        max_gap (float): seconds
    Returns:
        :obj:`list` of :obj:`list` of :obj:`Point`: the trips, each with at
            least two points, in order
    """
    if len(points) < 2:
        return []

    stays, breaks = _find_stays(points, stay_radius, stay_min_time, max_gap)
    stays = _merge_returns(stays, breaks, stay_radius)

    # (end, next begin, bounded): a trip ends at a stay's arrival and the next
    # begins at its departure; at a gap break it ends before the gap and
    # begins after it. Between two stays movement is always a trip (they were
    # not merged, so they are different places); elsewhere it must go somewhere
    last = len(points) - 1
    starts_after_break = set(breaks)
    cuts = []
    for stay in stays:
        arrive, leave = _core(points, stay, stay_radius / 2.0,
                              stay[0] != 0 and stay[0] not in starts_after_break,
                              stay[1] != last and stay[1] + 1 not in starts_after_break)
        cuts.append((arrive, leave, True))
    cuts.extend((k - 1, k, False) for k in breaks)
    cuts.sort()

    trips = []
    begin, after_stay = 0, False
    for end, next_begin, at_stay in cuts:
        if end > begin and ((after_stay and at_stay) or
                            _goes_somewhere(points, begin, end, stay_radius)):
            trips.append(points[begin:end + 1])
        if next_begin > begin:
            begin, after_stay = next_begin, at_stay
    if last > begin and _goes_somewhere(points, begin, last, stay_radius):
        trips.append(points[begin:last + 1])

    if debug:
        print('stays: %d, gap breaks: %d, trips: %d' % (len(stays), len(breaks), len(trips)))
    return trips
