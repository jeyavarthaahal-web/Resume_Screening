"""Conservative experience fit score; a maximum does not penalize qualified experience."""


def experience_score(candidate_years: float | int | None, minimum: float | int | None, maximum: float | int | None = None) -> float:
    if minimum is None and maximum is None: return 100.0
    if candidate_years is None: return 50.0
    years = max(0.0, float(candidate_years))
    minimum_years = max(0.0, float(minimum)) if minimum is not None else None
    if minimum_years is None or minimum_years == 0 or years >= minimum_years: return 100.0
    return round(max(0.0, min(100.0, years / minimum_years * 100)), 2)
