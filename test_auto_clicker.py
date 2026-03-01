import math
import unittest
from auto_clicker import ClickPattern, ClickTracker, AutoClickState, MIN_CLICK_INTERVAL


def _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0):
    return ClickPattern(mean_interval=mean, std_interval=std,
                        mean_hold=mean_hold, std_hold=std_hold)


def _press(tracker, down, up):
    """Helper: record a complete press on tracker, return (tracker, pattern)."""
    return tracker.record_down(down).record_up(up)


class TestClickPattern(unittest.TestCase):
    def test_compute_interval_zero_sample(self):
        p = _pattern(mean=0.3, std=0.05)
        self.assertAlmostEqual(p.compute_interval(0.0), 0.3)

    def test_compute_interval_positive_sample(self):
        p = _pattern(mean=0.3, std=0.1)
        self.assertAlmostEqual(p.compute_interval(1.0), 0.4)

    def test_compute_interval_negative_sample(self):
        p = _pattern(mean=0.3, std=0.1)
        self.assertAlmostEqual(p.compute_interval(-1.0), 0.2)

    def test_compute_interval_clamped_to_minimum(self):
        p = _pattern(mean=0.01, std=1.0)
        self.assertAlmostEqual(p.compute_interval(-10.0), MIN_CLICK_INTERVAL)

    def test_compute_interval_exactly_at_minimum(self):
        p = _pattern(mean=MIN_CLICK_INTERVAL, std=0.0)
        self.assertAlmostEqual(p.compute_interval(0.0), MIN_CLICK_INTERVAL)

    def test_compute_hold_zero_sample(self):
        p = _pattern(mean_hold=0.08, std_hold=0.01)
        self.assertAlmostEqual(p.compute_hold(0.0), 0.08)

    def test_compute_hold_positive_sample(self):
        p = _pattern(mean_hold=0.08, std_hold=0.01)
        self.assertAlmostEqual(p.compute_hold(1.0), 0.09)

    def test_compute_hold_clamped_to_minimum(self):
        p = _pattern(mean_hold=0.01, std_hold=1.0)
        self.assertAlmostEqual(p.compute_hold(-10.0), MIN_CLICK_INTERVAL)


class TestClickTracker(unittest.TestCase):
    def test_first_press_no_pattern(self):
        t, pattern = _press(ClickTracker(), 1.0, 1.05)
        self.assertIsNone(pattern)
        self.assertEqual(t.press_times, (1.0,))
        self.assertAlmostEqual(t.hold_durations[0], 0.05)

    def test_second_press_no_pattern(self):
        t, _ = _press(ClickTracker(), 1.0, 1.05)
        t, pattern = _press(t, 1.2, 1.25)
        self.assertIsNone(pattern)
        self.assertEqual(t.press_times, (1.0, 1.2))

    def test_triple_click_returns_pattern(self):
        t, _ = _press(ClickTracker(), 1.0, 1.05)
        t, _ = _press(t, 1.2, 1.25)
        t, pattern = _press(t, 1.4, 1.45)
        self.assertIsNotNone(pattern)
        self.assertAlmostEqual(pattern.mean_interval, 0.2)

    def test_triple_click_equal_intervals_std_is_zero(self):
        t, _ = _press(ClickTracker(), 0.0, 0.05)
        t, _ = _press(t, 0.2, 0.25)
        t, pattern = _press(t, 0.4, 0.45)
        self.assertIsNotNone(pattern)
        self.assertAlmostEqual(pattern.std_interval, 0.0)

    def test_triple_click_unequal_intervals_std(self):
        t, _ = _press(ClickTracker(), 0.0, 0.05)
        t, _ = _press(t, 0.1, 0.15)   # i1 = 0.1
        t, pattern = _press(t, 0.4, 0.45)  # i2 = 0.3
        self.assertIsNotNone(pattern)
        mean = (0.1 + 0.3) / 2
        expected_std = math.sqrt(((0.1 - mean) ** 2 + (0.3 - mean) ** 2) / 2)
        self.assertAlmostEqual(pattern.mean_interval, mean)
        self.assertAlmostEqual(pattern.std_interval, expected_std)

    def test_triple_click_equal_holds_mean_and_std(self):
        t, _ = _press(ClickTracker(), 0.0, 0.05)   # hold 50ms
        t, _ = _press(t, 0.2, 0.25)                # hold 50ms
        t, pattern = _press(t, 0.4, 0.45)          # hold 50ms
        self.assertIsNotNone(pattern)
        self.assertAlmostEqual(pattern.mean_hold, 0.05)
        self.assertAlmostEqual(pattern.std_hold, 0.0)

    def test_triple_click_unequal_holds_std(self):
        t, _ = _press(ClickTracker(), 0.0, 0.03)   # hold 30ms
        t, _ = _press(t, 0.2, 0.25)                # hold 50ms
        t, pattern = _press(t, 0.4, 0.47)          # hold 70ms
        self.assertIsNotNone(pattern)
        mean_h = (0.03 + 0.05 + 0.07) / 3
        std_h = math.sqrt(((0.03 - mean_h)**2 + (0.05 - mean_h)**2 + (0.07 - mean_h)**2) / 3)
        self.assertAlmostEqual(pattern.mean_hold, mean_h)
        self.assertAlmostEqual(pattern.std_hold, std_h)

    def test_tracker_resets_after_triple_click(self):
        t, _ = _press(ClickTracker(), 0.0, 0.05)
        t, _ = _press(t, 0.2, 0.25)
        t, pattern = _press(t, 0.4, 0.45)
        self.assertIsNotNone(pattern)
        self.assertEqual(t.press_times, ())
        self.assertEqual(t.hold_durations, ())

    def test_gap_too_large_between_first_and_second_no_pattern(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = _press(t, 0.0, 0.05)
        t, _ = _press(t, 0.6, 0.65)   # gap > max_interval
        t, pattern = _press(t, 0.9, 0.95)
        self.assertIsNone(pattern)

    def test_gap_too_large_between_second_and_third_no_pattern(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = _press(t, 0.0, 0.05)
        t, _ = _press(t, 0.2, 0.25)
        t, pattern = _press(t, 0.9, 0.95)  # gap > max_interval
        self.assertIsNone(pattern)

    def test_stale_presses_pruned(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = _press(t, 0.0, 0.05)
        t, _ = _press(t, 2.0, 2.05)   # cutoff=0.5 → 0.0 pruned
        self.assertNotIn(0.0, t.press_times)

    def test_fourth_press_after_triple_starts_fresh(self):
        t, _ = _press(ClickTracker(), 0.0, 0.05)
        t, _ = _press(t, 0.2, 0.25)
        t, _ = _press(t, 0.4, 0.45)   # triple → reset
        t, pattern = _press(t, 0.6, 0.65)
        self.assertIsNone(pattern)
        self.assertEqual(t.press_times, (0.6,))

    def test_max_interval_exactly_at_boundary_accepted(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = _press(t, 0.0, 0.05)
        t, _ = _press(t, 0.5, 0.55)
        t, pattern = _press(t, 1.0, 1.05)
        self.assertIsNotNone(pattern)

    def test_max_interval_just_over_boundary_rejected(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = _press(t, 0.0, 0.05)
        t, _ = _press(t, 0.5 + 1e-9, 0.55 + 1e-9)
        t, pattern = _press(t, 1.0, 1.05)
        self.assertIsNone(pattern)

    def test_record_up_without_record_down_is_noop(self):
        t = ClickTracker()
        t2, pattern = t.record_up(1.0)
        self.assertIsNone(pattern)
        self.assertIs(t2, t)


class TestAutoClickState(unittest.TestCase):
    def test_inactive_tick_returns_no_press_no_release(self):
        state = AutoClickState(active=False, pattern=_pattern())
        state2, should_press, should_release = state.tick(999.0, 0.0, 0.0)
        self.assertFalse(should_press)
        self.assertFalse(should_release)
        self.assertIs(state2, state)

    def test_activate_schedules_first_click(self):
        p = _pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        self.assertTrue(state.active)
        self.assertAlmostEqual(state.next_click_at, 1.2)

    def test_tick_before_next_click_at_no_press(self):
        p = _pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, should_press, should_release = state.tick(1.1, 0.0, 0.0)
        self.assertFalse(should_press)
        self.assertFalse(should_release)
        self.assertIs(state2, state)

    def test_tick_at_next_click_at_fires_press(self):
        p = _pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        _, should_press, should_release = state.tick(1.2, 0.0, 0.0)
        self.assertTrue(should_press)
        self.assertFalse(should_release)

    def test_tick_after_next_click_at_fires_press(self):
        p = _pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        _, should_press, _ = state.tick(1.5, 0.0, 0.0)
        self.assertTrue(should_press)

    def test_tick_advances_next_click_at(self):
        p = _pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, should_press, _ = state.tick(1.2, 0.0, 0.0)
        self.assertTrue(should_press)
        self.assertAlmostEqual(state2.next_click_at, 1.4)

    def test_tick_next_click_at_advances_from_scheduled_not_now(self):
        p = _pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _, _ = state.tick(1.5, 0.0, 0.0)
        self.assertAlmostEqual(state2.next_click_at, 1.4)

    def test_after_press_state_is_holding(self):
        p = _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, should_press, _ = state.tick(1.2, 0.0, 0.0)
        self.assertTrue(should_press)
        self.assertTrue(state2.holding)

    def test_holding_state_schedules_key_up(self):
        p = _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _, _ = state.tick(1.2, 0.0, 0.0)
        self.assertAlmostEqual(state2.key_up_at, 1.25)

    def test_holding_no_release_before_key_up_at(self):
        p = _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _, _ = state.tick(1.2, 0.0, 0.0)   # fires press, holding=True
        _, should_press, should_release = state2.tick(1.24, 0.0, 0.0)
        self.assertFalse(should_press)
        self.assertFalse(should_release)

    def test_release_fires_at_key_up_at(self):
        p = _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _, _ = state.tick(1.2, 0.0, 0.0)   # press; key_up_at=1.25
        _, should_press, should_release = state2.tick(1.25, 0.0, 0.0)
        self.assertFalse(should_press)
        self.assertTrue(should_release)

    def test_after_release_not_holding(self):
        p = _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _, _ = state.tick(1.2, 0.0, 0.0)   # press
        state3, _, _ = state2.tick(1.25, 0.0, 0.0)  # release
        self.assertFalse(state3.holding)

    def test_next_click_preserved_through_hold_phase(self):
        p = _pattern(mean=0.2, std=0.0, mean_hold=0.05, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _, _ = state.tick(1.2, 0.0, 0.0)   # press; next_click_at=1.4
        state3, _, _ = state2.tick(1.25, 0.0, 0.0)  # release
        self.assertAlmostEqual(state3.next_click_at, 1.4)

    def test_deactivate_clears_active_flag(self):
        p = _pattern()
        state = AutoClickState(pattern=p).activate(1.0, 0.0).deactivate()
        self.assertFalse(state.active)

    def test_no_pattern_uses_min_interval(self):
        state = AutoClickState().activate(now=1.0, gauss_sample=0.0)
        self.assertAlmostEqual(state.next_click_at, 1.0 + MIN_CLICK_INTERVAL)

    def test_sequence_of_clicks(self):
        p = _pattern(mean=0.1, std=0.0, mean_hold=MIN_CLICK_INTERVAL, std_hold=0.0)
        state = AutoClickState(pattern=p).activate(now=0.0, gauss_sample=0.0)
        presses = 0
        now = 0.0
        for _ in range(10):
            now += 0.1
            state, should_press, _ = state.tick(now, 0.0, 0.0)   # fires press
            if should_press:
                presses += 1
            now += MIN_CLICK_INTERVAL
            state, _, _ = state.tick(now, 0.0, 0.0)               # fires release
        self.assertEqual(presses, 10)


if __name__ == "__main__":
    unittest.main()
