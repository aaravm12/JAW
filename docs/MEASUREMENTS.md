# Measurement definitions and limitations

Version 0.1.0. These measurements describe a model's estimate of visible facial geometry in a 2-D image. They do not measure mandibular position, condylar travel, occlusion, muscle activation, bite force, fatigue, neurological dysfunction, inflammation, or recovery. No physical length calibration is performed.

## Observed geometry

MediaPipe Tasks produces normalized image landmark coordinates. Convert to pixels first: `p_i = (x_i * width, y_i * height)`. Using unscaled normalized coordinates would distort distances for nonsquare images.

- Upper inner lip: **13**; lower inner lip: **14**.
- Outer eye corners: **33**, **263** (stable reference relative to lips, still affected by perspective/expression).
- Mouth corners: **61**, **291**.
- Additional debug overlay landmarks: nose **1**, forehead **10**, chin **152**. The chin is not used as a direct mandibular measurement.
- Reference `R = ||p_263 - p_33||`.
- Raw normalized opening `O = ||p_14 - p_13|| / R`, dimensionless.
- Image horizontal eye axis `u = (p_263 - p_33) / R`.
- Raw lateral mouth-center projection `L = dot((p_61+p_291)/2 - (p_33+p_263)/2, u) / R`.
- Reported lateral proxy `L - median(L during calibration)`. This is a mouth-center projection, not jaw deviation. It remains in engineering export rather than receiving clinical interpretation.

The detector is configured for up to two faces so it can reject multiple faces. `num_faces=1` would hide additional faces from this check. A second face missed by ML cannot be ruled out. Detection, presence, and tracking thresholds are each 0.65. The returned task result does not expose a calibrated per-frame confidence score; none is fabricated. A missing detection can mean low confidence or an absent face.

Approximate yaw/pitch/roll come from the facial transformation matrix after removing scale using a polar decomposition. They are image-alignment quality checks, not validated anatomical head angles. Mouth expressions can perturb pose estimates.

## Calibration

Hold a relaxed jaw and a forward-facing head for at least two seconds and 30 contiguous valid frames. Reference statistics are medians; recorded quality includes reference frame count, duration, eye-distance coefficient of variation, lip-opening SD, center-position SD, and pose SD.

Engineering acceptance thresholds: eye distance 15–55% of image width; eye midpoint within x=25–75%, y=18–60%; absolute yaw/pitch ≤20°, roll ≤15°. Stability requires eye-distance CV ≤3%, maximum center SD ≤0.012 of the corresponding image dimension, maximum pose SD ≤3°, opening SD ≤0.015 ratios. These are adjustable development heuristics, not validated clinical cutoffs or a calibration accuracy score.

A distance change >15%, eye-center shift >0.10 normalized image distance, or pose change >12° relative to calibration latches `camera_or_head_repositioned`. Stop and recalibrate; returning the camera does not silently restore validity. Smaller changes can still bias geometry. Eye-distance normalization reduces uniform scaling effects; it cannot correct perspective or recover 3-D jaw position.

## Preprocessing and timing

Live frame time is `time.monotonic() - acquisition_origin`. It is sampled immediately after capture returns; this is not the sensor exposure timestamp. UTC ISO wall time is saved separately as session metadata. Video uses decoded presentation timestamps minus the first timestamp, including variable frame intervals. Missing/nonincreasing video timestamps fail explicitly. Synthetic CLI time is frame index / configured synthetic FPS. Live demo uses a monotonic clock.

MediaPipe requires increasing integer milliseconds; only the detector call rounds and clamps these values. Original source times remain in measurements and exports.

An interval above 0.25 s, or above `max(0.15 s, 3 × median recent usable intervals)`, flags a frame gap. Impossible landmark geometry, missing/multiple faces, positioning, rotation, absent calibration, a displaced reference, or a raw opening jump over 4 ratios/s invalidate the processed sample. Available raw coordinates remain; filtered fields become null. Missing frames are not interpolated. The first valid sample after a break restarts the filter with no velocity estimate. A gap records unavailable time, not an exact count of physically dropped camera frames.

Filter: first-order exponential smoothing with `alpha = 1 - exp(-dt / tau)`, `tau=0.08 s`. Velocity is a backward difference of the smoothed signal divided by actual dt, in ratios/s. Smoothing reduces jitter and introduces timing/amplitude bias. Outlier rejection and all thresholds must be evaluated empirically for a study population.

## Metric classes

| Class | Fields | Interpretation |
|---|---|---|
| Observed landmark geometry | selected x/y, eye distance, raw lip opening, eye center | Geometry estimated from image pixels by the detector, not direct anatomical truth |
| Derived kinematics | smoothed opening, velocity, complete excursions, opening/closing timing | Calculations on usable contiguous observations |
| Exploratory functional descriptors | phase means/peaks, cycle amplitude/duration SD, frequency, lateral projection, cross-session amplitude changes | Descriptive, sensitive to protocol, camera, quality and threshold choices |
| Unvalidated clinical hypotheses | recovery, fatigue, pain risk, abnormality | Not computed; no clinical scoring or inference |

A complete movement excursion requires calibrated-rest+0.025 → at least calibrated-rest+0.08 → rest+0.025. Start is the last low sample before departure; end is the first low sample on return. Peak divides opening/closing times. Excursions outside 0.5–15 s are excluded. Gaps, invalid frames, pauses and phase boundaries cancel incomplete excursions. An initially open mouth does not count until it first rests.

`duration`/`mean_cycle_s` are **threshold-to-threshold excursion times**, excluding time spent below the low threshold. They are not a full repetition period. `frequency_hz` is the reciprocal of mean peak-to-peak period across consecutive complete excursions in the same uninterrupted phase; it needs at least two cycles. Amplitude is peak minus the start sample. SD uses sample SD (n−1); a single cycle has no SD. Means across frames are sample-weighted, not continuous-time integrals. Variable-rate sampling therefore affects descriptive averages; source times are provided for alternative research analyses.

Phase summaries use valid running rows only. Pause rows remain exported with blank processed values. The final state-transition frame is labeled `finished` and excluded. Preview graphs can show fewer points than stored measurements because the preview queue prioritizes responsiveness. Results graphs use the complete saved rows, with gaps for invalid data.

Cross-session comparison requires one participant, one source kind, matching algorithm/settings/runtime/model, complete unskipped assessments, ≥80% valid controlled-phase frames and ≥2 cycles. The 80% criterion is an engineering inclusion rule. Calibration and source differences can still confound comparisons. No changes are labeled improvement or disease progression. Dates are acquisition/analysis dates; imported-video metadata does not pretend to know the original recording date.

## Sources

- [MediaPipe Face Landmarker Python API guide](https://developers.google.com/edge/mediapipe/solutions/vision/face_landmarker/python)
- [MediaPipe Face Landmarker result API](https://ai.google.dev/edge/api/mediapipe/python/mp/tasks/vision/FaceLandmarker)
- [Versioned Google model download](https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task)
- [PyAV time documentation](https://pyav.org/docs/stable/api/time.html)

The equations, filtering, thresholds and validation fixture behavior are implemented here. They are not a clinically validated TMD protocol.

## Checkpoint 4 live indicators

- **Processing FPS** is `(n-1)/(last-first)` over processing-completion monotonic timestamps in the latest two seconds. It includes acquisition and inference time, is independent of video presentation time, and is not the camera's advertised sensor FPS. It starts blank and clears after a stall or input closure.
- **Frame size** comes from the actual decoded/captured array, in pixels. Requested capture size is not assumed to be the delivered resolution.
- **Phase peak** is the maximum valid smoothed opening observed during the current running assessment phase. It resets at a phase boundary or new assessment. It is historical and may remain visible during tracking loss or pause.
- **Movement frequency** uses the same complete-cycle detector as saved analysis: reciprocal mean peak-to-peak interval for the current uninterrupted phase. At least two completed cycles are required. Invalid frames, pauses, phase changes, restart, and absence of a new peak for the maximum cycle duration clear the live frequency. It never uses the requested pacing cue as a measured value. Saved phase summaries can aggregate multiple valid segments; live frequency only describes the current segment.
- The cycle counter remains the total complete-cycle count for the current assessment. No calibration or paused frames contribute.
