from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Optional, Tuple

MIN_CLICK_INTERVAL = 0.01  # seconds


@dataclass(frozen=True)
class ClickPattern:
    mean_interval: float
    std_interval: float

    def compute_interval(self, gauss_sample: float) -> float:
        return max(MIN_CLICK_INTERVAL, self.mean_interval + self.std_interval * gauss_sample)


@dataclass(frozen=True)
class ClickTracker:
    press_times: Tuple[float, ...] = ()
    max_interval: float = 0.5

    def record_press(self, timestamp: float) -> Tuple[ClickTracker, Optional[ClickPattern]]:
        cutoff = timestamp - 3 * self.max_interval
        pruned = tuple(t for t in self.press_times if t >= cutoff)
        updated = pruned + (timestamp,)

        if len(updated) < 3:
            return ClickTracker(press_times=updated, max_interval=self.max_interval), None

        # Check the last 3 presses form a triple-click
        t1, t2, t3 = updated[-3], updated[-2], updated[-1]
        i1 = t2 - t1
        i2 = t3 - t2
        if i1 > self.max_interval or i2 > self.max_interval:
            return ClickTracker(press_times=updated, max_interval=self.max_interval), None

        mean = (i1 + i2) / 2
        std = math.sqrt(((i1 - mean) ** 2 + (i2 - mean) ** 2) / 2)
        pattern = ClickPattern(mean_interval=mean, std_interval=std)
        return ClickTracker(press_times=(), max_interval=self.max_interval), pattern


@dataclass(frozen=True)
class AutoClickState:
    active: bool = False
    pattern: Optional[ClickPattern] = None
    next_click_at: float = 0.0

    def activate(self, now: float, gauss_sample: float) -> AutoClickState:
        interval = self.pattern.compute_interval(gauss_sample) if self.pattern else MIN_CLICK_INTERVAL
        return AutoClickState(active=True, pattern=self.pattern, next_click_at=now + interval)

    def deactivate(self) -> AutoClickState:
        return AutoClickState(active=False, pattern=self.pattern, next_click_at=0.0)

    def tick(self, now: float, gauss_sample: float) -> Tuple[AutoClickState, bool]:
        if not self.active or now < self.next_click_at:
            return self, False
        interval = self.pattern.compute_interval(gauss_sample) if self.pattern else MIN_CLICK_INTERVAL
        new_state = AutoClickState(active=True, pattern=self.pattern, next_click_at=self.next_click_at + interval)
        return new_state, True
