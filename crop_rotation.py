"""Explainable multi-season rotation comparison using user-supplied profiles."""

from __future__ import annotations


def compare_rotations(sequences, farm_soil_ec=None):
    """Compare plans from explicit crop profile inputs; never infer yield outcomes.

    Each crop record must include name, weekly water mm, family, salt_tolerance
    (dS/m or None), and legume bool. Scores are transparent planning heuristics.
    """
    rows = []
    for sequence in sequences:
        crops = sequence["crops"]
        water = sum(float(c["water_mm_week"]) for c in crops)
        families = [c.get("family", "Unknown").strip().lower() for c in crops]
        family_diversity = len(set(families)) / max(len(families), 1)
        legumes = sum(bool(c.get("legume")) for c in crops)
        sustainability = None if len(crops) < 2 else min(
            100.0,
            family_diversity * 65
            + min(legumes, 1) * 20
            + (15 if len(set(families)) == len(families) else 0),
        )
        tolerances = [float(c["salt_tolerance_ds_m"]) for c in crops if c.get("salt_tolerance_ds_m") is not None]
        ec_note = "Farm soil EC not entered; salinity fit is not scored."
        salt_fit = None
        if farm_soil_ec is not None and tolerances:
            salt_fit = sum(float(farm_soil_ec) <= threshold for threshold in tolerances) / len(tolerances) * 100
            ec_note = "Heuristic comparison only: entered EC and crop reference must use comparable soil test methods."
        rows.append({"name": sequence["name"], "seasons": len(crops), "water_total_mm_week": water,
                     "water_mean_mm_week": water / max(len(crops), 1), "sustainability_score": sustainability,
                     "salinity_fit_pct": salt_fit, "ec_note": ec_note,
                     "families": " → ".join(c.get("family", "Unspecified") for c in crops),
                     "crops": " → ".join(c["name"] for c in crops),
                     "assumption": "Water values and crop properties are planning inputs; score is an unvalidated heuristic, not yield or soil outcome prediction."})
    return rows
