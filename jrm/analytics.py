from collections import Counter
import numpy as np
from .cycles import CycleDetector
from .config import PHASES, Settings


def _mean(a):
    return float(np.mean(a)) if len(a) else None


def _sd(a):
    return float(np.std(a, ddof=1)) if len(a) > 1 else None


def analyze(rows, cfg: Settings, resting: float):
    detector = CycleDetector(cfg, resting)
    cycles = []
    previous_segment = None
    previous_cycle = None
    for r in rows:
        segment = (r["phase"], r.get("segment", 0))
        if segment != previous_segment:
            detector.reset()
            previous_cycle = None
        if not r["valid"] or r.get("recording_state") != "running":
            previous_cycle = None
        previous_segment = segment
        c = detector.add(r["source_t"], r.get("opening"), r["valid"] and r.get("recording_state") == "running")
        if c:
            c["phase"] = r["phase"]
            c["period_s"] = c["peak_t"] - previous_cycle["peak_t"] if previous_cycle else None
            previous_cycle = c
            cycles.append(c)
    summaries = {}
    for phase in PHASES:
        all_phase = [r for r in rows if r["phase"] == phase and r.get("recording_state") == "running"]
        usable = [r for r in all_phase if r["valid"] and r.get("opening") is not None]
        values = [r["opening"] for r in usable]
        pc = [c for c in cycles if c["phase"] == phase]
        durations, amplitudes = [c["duration"] for c in pc], [c["amplitude"] for c in pc]
        summaries[phase] = {
            "frames": len(all_phase), "valid_frames": len(usable),
            "valid_fraction": len(usable) / len(all_phase) if all_phase else None,
            "mean_opening": _mean(values), "max_opening": max(values) if values else None,
            "opening_sd": _sd(values), "complete_cycles": len(pc),
            "mean_cycle_s": _mean(durations), "cycle_sd_s": _sd(durations),
            "frequency_hz": 1 / _mean([c["period_s"] for c in pc if c["period_s"] is not None]) if any(c["period_s"] is not None for c in pc) else None,
            "mean_amplitude": _mean(amplitudes), "amplitude_sd": _sd(amplitudes),
            "mean_opening_s": _mean([c["opening_duration"] for c in pc]),
            "mean_closing_s": _mean([c["closing_duration"] for c in pc]),
            "mean_abs_velocity": _mean([abs(r["velocity"]) for r in usable if r.get("velocity") is not None]),
        }
    flags = Counter(f for r in rows for f in r["flags"].split("|") if f)
    positive_dt = [r["dt"] for r in rows if r.get("dt") and r["dt"] > 0]
    return {"phases": summaries, "cycles": cycles, "quality_flags": dict(flags),
            "median_sample_hz": 1 / float(np.median(positive_dt)) if positive_dt else None,
            "recovery": "Recovery time not established from this measurement."}


def compare_sessions(sessions):
    if len(sessions) < 2:
        raise ValueError("Choose at least two saved sessions.")
    if len({s["participant_id"] for s in sessions}) != 1:
        raise ValueError("Compare sessions for the same anonymous participant.")
    if len({s["source_kind"] for s in sessions}) != 1:
        raise ValueError("Synthetic, webcam, and offline-video sessions must be compared separately.")
    if len({s["algorithm_version"] for s in sessions}) != 1 or any(s["settings"] != sessions[0]["settings"] for s in sessions):
        raise ValueError("Comparison requires matching settings and algorithm versions.")
    if any(s.get("runtime") != sessions[0].get("runtime") for s in sessions):
        raise ValueError("Comparison requires a matching recorded runtime and model; changed software may change measurements.")
    if any(s["status"] != "finished" or s.get("skipped") for s in sessions):
        raise ValueError("Comparison requires complete, unskipped assessments.")
    results = []
    for s in sorted(sessions, key=lambda x: x["started_at"]):
        p = s["analysis"]["phases"]["controlled"]
        if p["valid_fraction"] is None or p["valid_fraction"] < .8 or p["complete_cycles"] < 2:
            raise ValueError("Insufficient controlled-movement data: need ≥80% valid frames and ≥2 complete cycles.")
        results.append({"session_id": s["session_id"], "date": s["started_at"],
                        "mean_amplitude": p["mean_amplitude"], "mean_cycle_s": p["mean_cycle_s"]})
    baseline = results[0]
    for r in results:
        r["amplitude_change"] = r["mean_amplitude"] - baseline["mean_amplitude"]
    return results
