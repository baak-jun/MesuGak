"""Target allocation logic for Mesugak V2 paper trading."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AllocationConfig:
    max_positions: int = 5
    max_position_weight: float = 0.25
    min_confidence: float = 65.0


def _bounded_pct(value: float) -> float:
    return min(max(float(value), 0.0), 1.0)


def _confidence(item: dict) -> float:
    return float(item.get("confidenceScore", 0) or 0)


def _allocate_with_caps(selected: list[dict], investable: float, max_weight: float) -> dict[str, float]:
    remaining = {str(item.get("code")): _confidence(item) for item in selected if item.get("code")}
    weights = dict.fromkeys(remaining, 0.0)
    remaining_weight = investable

    while remaining and remaining_weight > 0:
        total_score = sum(remaining.values())
        if total_score <= 0:
            even_weight = remaining_weight / len(remaining)
            capped = [code for code in remaining if even_weight >= max_weight]
            if not capped:
                for code in remaining:
                    weights[code] += even_weight
                break
        else:
            capped = [
                code for code, score in remaining.items()
                if remaining_weight * (score / total_score) >= max_weight
            ]
            if not capped:
                for code, score in remaining.items():
                    weights[code] += remaining_weight * (score / total_score)
                break

        for code in capped:
            add_weight = max(0.0, max_weight - weights[code])
            weights[code] += add_weight
            remaining_weight -= add_weight
            remaining.pop(code)

    return weights


def build_target_allocations(candidates: list[dict], cash_target_pct: float, config: AllocationConfig | None = None) -> dict:
    cfg = config or AllocationConfig()
    cash_target = _bounded_pct(cash_target_pct)
    max_positions = max(0, cfg.max_positions)
    max_position_weight = _bounded_pct(cfg.max_position_weight)
    eligible = [
        item for item in candidates
        if _confidence(item) >= cfg.min_confidence
        and item.get("signal", {}).get("action", "BUY_CANDIDATE") not in {"EXIT", "REDUCE"}
        and item.get("code")
    ]
    eligible.sort(key=_confidence, reverse=True)
    selected = eligible[:max_positions]

    investable = max(0.0, 1.0 - cash_target)
    weights = _allocate_with_caps(selected, investable, max_position_weight)

    positions = []
    for item in selected:
        target_weight = weights.get(str(item.get("code")), 0.0)
        positions.append({
            "id": item.get("id"),
            "code": item.get("code"),
            "name": item.get("name"),
            "targetWeight": round(target_weight, 4),
            "confidenceScore": _confidence(item),
        })

    used = sum(float(item["targetWeight"]) for item in positions)
    return {
        "cashTargetPct": round(max(cash_target, 1.0 - used), 4),
        "positions": positions,
    }
