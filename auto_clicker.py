from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Optional, Tuple

MIN_CLICK_INTERVAL = 0.01  # seconds


@dataclass(frozen=True)
class ClickPattern:
    mean_interval: float
    std_interval: float
    mean_hold: float
    std_hold: float

    def compute_interval(self, gauss_sample: float) -> float:
        return max(MIN_CLICK_INTERVAL, self.mean_interval + self.std_interval * gauss_sample)

    def compute_hold(self, gauss_sample: float) -> float:
        return max(MIN_CLICK_INTERVAL, self.mean_hold + self.std_hold * gauss_sample)

    def __str__(self) -> str:
        return (
            f"{self.mean_interval*1000:.1f}ms ± {self.std_interval*1000:.1f}ms"
            f" (hold {self.mean_hold*1000:.1f}ms ± {self.std_hold*1000:.1f}ms)"
        )


@dataclass(frozen=True)
class ClickTracker:
    press_times: Tuple[float, ...] = ()      # KEY_DOWN timestamps of completed presses
    hold_durations: Tuple[float, ...] = ()   # hold durations of completed presses (parallel)
    pending_down: Optional[float] = None     # KEY_DOWN timestamp of in-progress press

    def __str__(self) -> str:
        n = len(self.press_times)
        return f"ClickTracker({n} press{'es' if n != 1 else ''})"

    def record_down(self, timestamp: float) -> ClickTracker:
        return ClickTracker(
            press_times=self.press_times,
            hold_durations=self.hold_durations,
            pending_down=timestamp,
        )

    def record_up(self, timestamp: float) -> Tuple[ClickTracker, Optional[ClickPattern]]:
        if self.pending_down is None:
            return self, None
        hold = timestamp - self.pending_down
        down_time = self.pending_down

        new_times = self.press_times + (down_time,)
        new_holds = self.hold_durations + (hold,)

        if len(new_times) < 3:
            return ClickTracker(press_times=new_times, hold_durations=new_holds,
                                pending_down=None), None

        t1, t2, t3 = new_times[-3], new_times[-2], new_times[-1]
        i1 = t2 - t1
        i2 = t3 - t2

        mean_i = (i1 + i2) / 2
        std_i = math.sqrt(((i1 - mean_i) ** 2 + (i2 - mean_i) ** 2) / 2)

        h1, h2, h3 = new_holds[-3], new_holds[-2], new_holds[-1]
        mean_h = (h1 + h2 + h3) / 3
        std_h = math.sqrt(((h1 - mean_h) ** 2 + (h2 - mean_h) ** 2 + (h3 - mean_h) ** 2) / 3)

        pattern = ClickPattern(mean_interval=mean_i, std_interval=std_i,
                               mean_hold=mean_h, std_hold=std_h)
        return ClickTracker(press_times=(), hold_durations=(), pending_down=None), pattern


@dataclass(frozen=True)
class AutoClickState:
    active: bool = False
    pattern: Optional[ClickPattern] = None
    next_click_at: float = 0.0
    holding: bool = False    # key is currently pressed down
    key_up_at: float = 0.0  # when to release (valid only when holding=True)

    def __str__(self) -> str:
        if not self.active:
            return "AutoClickState(inactive)"
        phase = "holding" if self.holding else "waiting"
        pattern_str = str(self.pattern) if self.pattern else "no pattern"
        return f"AutoClickState({phase}, {pattern_str})"

    def activate(self, now: float, gauss_sample: float) -> AutoClickState:
        interval = self.pattern.compute_interval(gauss_sample) if self.pattern else MIN_CLICK_INTERVAL
        return AutoClickState(active=True, pattern=self.pattern,
                              next_click_at=now + interval, holding=False, key_up_at=0.0)

    def deactivate(self) -> AutoClickState:
        return AutoClickState(active=False, pattern=self.pattern,
                              next_click_at=0.0, holding=False, key_up_at=0.0)

    def tick(self, now: float, gauss_interval: float, gauss_hold: float) -> Tuple[AutoClickState, bool, bool]:
        """Returns (new_state, should_press, should_release)."""
        if not self.active:
            return self, False, False

        if self.holding:
            if now >= self.key_up_at:
                new_state = AutoClickState(active=True, pattern=self.pattern,
                                           next_click_at=self.next_click_at,
                                           holding=False, key_up_at=0.0)
                return new_state, False, True
            return self, False, False

        if now >= self.next_click_at:
            hold = self.pattern.compute_hold(gauss_hold) if self.pattern else MIN_CLICK_INTERVAL
            interval = self.pattern.compute_interval(gauss_interval) if self.pattern else MIN_CLICK_INTERVAL
            new_state = AutoClickState(active=True, pattern=self.pattern,
                                       next_click_at=self.next_click_at + interval,
                                       holding=True, key_up_at=now + hold)
            return new_state, True, False

        return self, False, False
