import math
import unittest
from auto_clicker import ClickPattern, ClickTracker, AutoClickState, MIN_CLICK_INTERVAL


class TestClickPattern(unittest.TestCase):
    def test_compute_interval_zero_sample(self):
        p = ClickPattern(mean_interval=0.3, std_interval=0.05)
        self.assertAlmostEqual(p.compute_interval(0.0), 0.3)

    def test_compute_interval_positive_sample(self):
        p = ClickPattern(mean_interval=0.3, std_interval=0.1)
        self.assertAlmostEqual(p.compute_interval(1.0), 0.4)

    def test_compute_interval_negative_sample(self):
        p = ClickPattern(mean_interval=0.3, std_interval=0.1)
        self.assertAlmostEqual(p.compute_interval(-1.0), 0.2)

    def test_compute_interval_clamped_to_minimum(self):
        p = ClickPattern(mean_interval=0.01, std_interval=1.0)
        self.assertAlmostEqual(p.compute_interval(-10.0), MIN_CLICK_INTERVAL)

    def test_compute_interval_exactly_at_minimum(self):
        p = ClickPattern(mean_interval=MIN_CLICK_INTERVAL, std_interval=0.0)
        self.assertAlmostEqual(p.compute_interval(0.0), MIN_CLICK_INTERVAL)


class TestClickTracker(unittest.TestCase):
    def test_first_press_no_pattern(self):
        t = ClickTracker()
        t, pattern = t.record_press(1.0)
        self.assertIsNone(pattern)
        self.assertEqual(t.press_times, (1.0,))

    def test_second_press_no_pattern(self):
        t = ClickTracker()
        t, _ = t.record_press(1.0)
        t, pattern = t.record_press(1.2)
        self.assertIsNone(pattern)
        self.assertEqual(t.press_times, (1.0, 1.2))

    def test_triple_click_returns_pattern(self):
        t = ClickTracker()
        t, _ = t.record_press(1.0)
        t, _ = t.record_press(1.2)
        t, pattern = t.record_press(1.4)
        self.assertIsNotNone(pattern)
        self.assertAlmostEqual(pattern.mean_interval, 0.2)

    def test_triple_click_equal_intervals_std_is_zero(self):
        t = ClickTracker()
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.2)
        t, pattern = t.record_press(0.4)
        self.assertIsNotNone(pattern)
        self.assertAlmostEqual(pattern.std_interval, 0.0)

    def test_triple_click_unequal_intervals_std(self):
        t = ClickTracker()
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.1)   # i1 = 0.1
        t, pattern = t.record_press(0.4)  # i2 = 0.3
        self.assertIsNotNone(pattern)
        mean = (0.1 + 0.3) / 2
        expected_std = math.sqrt(((0.1 - mean) ** 2 + (0.3 - mean) ** 2) / 2)
        self.assertAlmostEqual(pattern.mean_interval, mean)
        self.assertAlmostEqual(pattern.std_interval, expected_std)

    def test_tracker_resets_after_triple_click(self):
        t = ClickTracker()
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.2)
        t, pattern = t.record_press(0.4)
        self.assertIsNotNone(pattern)
        self.assertEqual(t.press_times, ())

    def test_gap_too_large_between_first_and_second_no_pattern(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.6)   # gap > max_interval
        t, pattern = t.record_press(0.9)
        self.assertIsNone(pattern)

    def test_gap_too_large_between_second_and_third_no_pattern(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.2)
        t, pattern = t.record_press(0.9)  # gap > max_interval
        self.assertIsNone(pattern)

    def test_stale_presses_pruned(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(2.0)   # cutoff=0.5 → 0.0 pruned
        self.assertNotIn(0.0, t.press_times)

    def test_fourth_press_after_triple_starts_fresh(self):
        t = ClickTracker()
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.2)
        t, _ = t.record_press(0.4)   # triple → reset
        t, pattern = t.record_press(0.6)
        self.assertIsNone(pattern)
        self.assertEqual(t.press_times, (0.6,))

    def test_max_interval_exactly_at_boundary_accepted(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.5)
        t, pattern = t.record_press(1.0)
        self.assertIsNotNone(pattern)

    def test_max_interval_just_over_boundary_rejected(self):
        t = ClickTracker(max_interval=0.5)
        t, _ = t.record_press(0.0)
        t, _ = t.record_press(0.5 + 1e-9)
        t, pattern = t.record_press(1.0)
        self.assertIsNone(pattern)


class TestAutoClickState(unittest.TestCase):
    def _pattern(self, mean=0.2, std=0.0):
        return ClickPattern(mean_interval=mean, std_interval=std)

    def test_inactive_tick_returns_no_click(self):
        state = AutoClickState(active=False, pattern=self._pattern())
        state2, clicked = state.tick(999.0, 0.0)
        self.assertFalse(clicked)
        self.assertIs(state2, state)

    def test_activate_schedules_first_click(self):
        p = self._pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        self.assertTrue(state.active)
        self.assertAlmostEqual(state.next_click_at, 1.2)

    def test_tick_before_next_click_at_no_click(self):
        p = self._pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, clicked = state.tick(1.1, 0.0)
        self.assertFalse(clicked)
        self.assertIs(state2, state)

    def test_tick_at_next_click_at_fires(self):
        p = self._pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        _, clicked = state.tick(1.2, 0.0)
        self.assertTrue(clicked)

    def test_tick_after_next_click_at_fires(self):
        p = self._pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        _, clicked = state.tick(1.5, 0.0)
        self.assertTrue(clicked)

    def test_tick_advances_next_click_at(self):
        p = self._pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, clicked = state.tick(1.2, 0.0)
        self.assertTrue(clicked)
        self.assertAlmostEqual(state2.next_click_at, 1.4)

    def test_tick_next_click_at_advances_from_scheduled_not_now(self):
        # Even if tick is called late, next is scheduled from previous next_click_at
        p = self._pattern(mean=0.2, std=0.0)
        state = AutoClickState(pattern=p).activate(now=1.0, gauss_sample=0.0)
        state2, _ = state.tick(1.5, 0.0)
        self.assertAlmostEqual(state2.next_click_at, 1.4)

    def test_deactivate_clears_active_flag(self):
        p = self._pattern()
        state = AutoClickState(pattern=p).activate(1.0, 0.0).deactivate()
        self.assertFalse(state.active)

    def test_no_pattern_uses_min_interval(self):
        state = AutoClickState().activate(now=1.0, gauss_sample=0.0)
        self.assertAlmostEqual(state.next_click_at, 1.0 + MIN_CLICK_INTERVAL)

    def test_sequence_of_clicks(self):
        p = self._pattern(mean=0.1, std=0.0)
        state = AutoClickState(pattern=p).activate(now=0.0, gauss_sample=0.0)
        clicks = 0
        now = 0.0
        for _ in range(10):
            now += 0.1
            state, fired = state.tick(now, 0.0)
            if fired:
                clicks += 1
        self.assertEqual(clicks, 10)


if __name__ == "__main__":
    unittest.main()
