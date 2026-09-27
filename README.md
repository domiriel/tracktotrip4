# TrackToTrip4
*TrackToTrip4* is a fork of [TrackToTrip3](https://github.com/dserafim1999/tracktotrip3), a Python 3 library used to process, simplify and clean GPS tracks. The original TrackToTrip3 library is no longer maintained, and this fork aims to keep it up to date with the latest Python versions and dependencies, plus adding new features and improvements.

The main goals are to transform a (gpx) **track into a trip**.

> **track**
> raw representation of a GPS recording. It is not precise, has noise and valuable information is hidden.


> **trip**
> result of one or more processed tracks. Its start and end points have semantic meaning, such as home, work or school. It has less errors and it's compressed, with as little information loss as possible. In short, a trip is an approximation of the true path recorded.

## Installing

You can install TrackToTrip4 by running the following command:

```
 $ python setup.py install
```

**NOTE:** TrackToTrip4 requires Microsoft Visual C++ 14.0. It can be found using the [Build Tools for Visual Studio 2022](https://visualstudio.microsoft.com/downloads/?q=build+tools)


**Python 3.x** is required.

## Overview

The starting points are the [Track](../master/tracktotrip3/track.py), [Segment](../master/tracktotrip3/segment.py) and [Point](../master/tracktotrip3/point.py) classes.

### [Track](../master/tracktotrip3/track.py)

Can be loaded from a GPX file:

```python
from tracktotrip4 import Track, Segment, Point

track = Track.from_gpx('file_to_track.gpx')
```

A track can be transformed into a trip with the method ` to_trip `. Transforming a track into a trip executes the following steps:

1. Smooths the segments, using the [kalman filter](../master/tracktotrip3/smooth.py)

2. Splits each segment into trips at stays and recording gaps, using [stay segmentation](../master/tracktotrip4/spatiotemporal_segmentation.py)

3. Compresses every segment, using [spatiotemporal-aware compression algorithm](../master/tracktotrip3/compression.py)

A track is composed by ` Segment `s, and each segment by ` Point `s.

It can be saved to a GPX file:

```python
with open('file.gpx', 'w') as f:
  f.write(track.to_gpx())
```

### [Segment](../master/tracktotrip3/segment.py)

A Segment holds the points, the transportation modes used, and the start and end semantic locations.

### [Point](../master/tracktotrip3/point.py)

A Point holds the position and time. Currently the library doesn't support elevation.


## Command line tools

In addition to the library, *TrackToTrip3* offers three command line tools outside of the library to manipulate GPS tracks and to generate classifier.

### tracktotrip_utils

```
usage: tracktotrip_utils.py [-h] [-a] [-s] [-o] [--eps EPS]
                            [--mintime MINTIME] [--seed SEED]
                            track [track ...] output_folder

Manipulate tracks

positional arguments:
  track              track to process, must be a gpx file
  output_folder

optional arguments:
  -h, --help         show this help message and exit
  -a, --anonymize    anonymizes tracks, by doing random rotations and
                     translations
  -s, --split        splits tracks so that each file contains a segment
  -o, --organize     takes all tracks and split them, naming them according
                     with their start date
  --eps EPS          max distance to other points. Used when spliting.
                     Defaults to 1.0
  --mintime MINTIME  minimum time required to split, in seconds. Defaults to
                     120
  --seed SEED        random number generator seed. Used when anonymizing
```

### tracktotrip_geolife_dataset

The **GeoLife Tracjectory dataset** can be found [here](https://www.microsoft.com/en-us/download/details.aspx?id=52367&from=http%3A%2F%2Fresearch.microsoft.com%2Fen-us%2Fdownloads%2Fb16d359d-d164-469e-9fd4-daa38f2b2e13%2F). The datasetFolder argument should point to the Data folder in the **GeoLife Trajectory dataset** folder.

```
usage: tracktotrip_geolife_dataset.py [-h] [-o outputFolder] [-d]
                                      datasetFolder

GeoLife Trajectory dataset transportation mode extractor. Extracts
transportation mode from the dataset, into individual files, annotated with
the following format: [transporation mode].[control].[nPoints].[original file
name].gpx



positional arguments:
  datasetFolder         Path to the GeoLife dataset folder

optional arguments:
  -h, --help            show this help message and exit
  -o outputFolder, --output outputFolder
                        Path to processed dataset

```

## License

[MIT license](../master/LICENSE)

## Canonical learning scalability (0.2.0)

`learn_trip` retains the best-match rule (maximum directional score, threshold
0.7, last candidate wins equal scores). It does not mutate input trips. Reusable
`SegmentIndex` objects avoid rebuilding the new trip's R-tree for each candidate;
`SegmentIndexCache` bounds retained indexes by points and entries and must be closed.
A conservative expanded-edge-box upper bound skips candidates that cannot beat the
current best score. Endpoint-only heuristics are deliberately not used: partial
and reversed routes remain eligible.

Merging queries nearby points through an index while preserving the previous
point-order and direction rules. Dense overlapping geometry can still be costly;
these changes do not promise constant-time matching for arbitrary routes.

`learn_trip(..., max_points=2048)` bounds the derived canonical geometry after
ordinary simplification. When the cap is reached, greatest-deviation subdivision
retains endpoints and reports the additional planar error in degrees as
`segment.representation_error` and in the optional `stats` dictionary. This is an
approximation of derived geometry only; keep original trip geometry for rebuilding.
Pass `max_points=None` to disable this cap for strict legacy geometry comparisons.
`stats` also reports candidate, scored and pruned counts. A bound on representation
size can change later matching decisions; compare those decisions on your fixtures.

## Stay segmentation (0.3.0)

`Track.to_trip(..., seg_stay_radius, seg_stay_min_time, seg_max_gap, ...)` replaces
`seg_eps`/`seg_min_time`. Trips are the movement between stays: periods of at
least `stay_min_time` seconds within `stay_radius` meters of their centre,
recorded (GPS left on) or not (a gap resuming at the same place). Stationary
stretches are not part of trips, so they are trimmed at the start and end of a
recording. A gap resuming elsewhere also ends a trip when it is longer than
`max_gap`, or when it lasts at least `stay_min_time` and is too slow to be travel
without signal. Movement that never leaves `stay_radius` of its start is dropped,
unless it goes from one stay to another. Segmentation is a single linear pass.

Tests (offline, with dependencies installed):

```sh
python -m unittest discover -s tracktotrip4/tests
```
