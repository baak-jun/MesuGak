"""Bounded second samples for the private paper-contest momentum experiment."""
from collections import deque
from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class MomentumConfig:
    enabled: bool = True
    score_ceiling: float = 50.0
    return_60s: float = 0.006
    return_180s: float = 0.010
    volume_ratio: float = 1.5
    max_spread: float = 0.005
    partial_drawdown: float = 0.008
    full_drawdown: float = 0.015


class MomentumWindow:
    """Six minutes of cumulative volume; subscription day totals are never flow.

    At most one sample per exchange second, independent of tick frequency.
    A long quote gap or a cumulative-volume reset requires a new warmup.
    """
    def __init__(self):
        self.points = deque()

    def add(self, tick):
        if not all(isfinite(v) for v in (tick.timestamp, tick.price, tick.cumulative_volume)):
            return
        if tick.price <= 0 or tick.cumulative_volume < 0:
            return
        point = (int(tick.timestamp), tick.price, tick.cumulative_volume)
        if self.points:
            last = self.points[-1]
            if point[0] < last[0]:
                return
            if point[0] - last[0] > 15 or point[2] < last[2]:
                self.points.clear()
            elif point[0] == last[0]:
                self.points[-1] = point
                return
        self.points.append(point)
        while len(self.points) > 1 and self.points[1][0] <= point[0] - 360:
            self.points.popleft()

    def snapshot(self):
        if not self.points or self.points[-1][0] - self.points[0][0] < 360:
            return {'surgeReady': False}
        now, price, volume = self.points[-1]
        def at(seconds):
            return next(p for p in reversed(self.points) if p[0] <= now - seconds)
        minute, three, six = at(60), at(180), at(360)
        recent = volume - minute[2]
        # Normalize observed durations instead of comparing ticks with minutes.
        baseline = (minute[2] - six[2]) / (minute[0] - six[0]) * 60
        recent_rate = recent / (now - minute[0]) * 60
        return {'surgeReady': baseline > 0 and recent > 0,
                'surgeReturn60s': price / minute[1] - 1,
                'surgeReturn180s': price / three[1] - 1,
                'surgeVolumeRatio': recent_rate / baseline if baseline > 0 else None,
                'surgeRecentVolume': recent, 'surgeBaselineVolumePerMinute': baseline}


def momentum_entry(snapshot, config: MomentumConfig):
    if not config.enabled or not snapshot.get('surgeReady'):
        return False
    spread = snapshot.get('spreadPct')
    if spread is None or not 0 <= spread <= config.max_spread:
        return False
    r60 = snapshot.get('surgeReturn60s', 0)
    r180 = snapshot.get('surgeReturn180s', 0)
    return bool(r60 > 0 and (r60 >= config.return_60s or r180 >= config.return_180s)
                and (snapshot.get('surgeVolumeRatio') or 0) >= config.volume_ratio)


def select_volume_watch(rows, protected, eligible, maximum):
    result = list(dict.fromkeys(protected))
    if len(result) > maximum:
        raise ValueError('Protected positions exceed subscription capacity')
    ranked = sorted(rows, key=lambda r: (-float(r.get('acml_vol') or 0), str(r.get('mksc_shrn_iscd') or r.get('stck_shrn_iscd') or '')))
    for row in ranked:
        code = str(row.get('mksc_shrn_iscd') or row.get('stck_shrn_iscd') or '').strip()
        if code in eligible and code not in result and len(result) < maximum:
            result.append(code)
    return result
