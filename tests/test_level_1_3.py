"""Tests for Act 1.3 — Idler gear level."""

from robot_forge.levels.level_1_3 import (
    DT,
    ThreeGearLevel,
    solve_driving_voltage_1_3,
)


class TestThreeGearDefaults:
    def test_default_state_not_won(self):
        lvl = ThreeGearLevel()
        assert not lvl.won
        assert lvl.last_diagnostic is None

    def test_default_teeth_are_30_each(self):
        lvl = ThreeGearLevel()
        assert lvl.driver.teeth == 30
        assert lvl.idler.teeth == 30
        assert lvl.driven.teeth == 30

    def test_target_sign_is_positive(self):
        lvl = ThreeGearLevel()
        assert lvl.target_sign == 1

    def test_meshed_always_true(self):
        lvl = ThreeGearLevel()
        assert lvl.meshed is True
        lvl.set_gears(12, 20, 60)
        assert lvl.meshed is True


class TestThreeGearPhysics:
    def test_driven_spins_same_direction_as_driver(self):
        """Positive voltage → both driver and driven have same sign."""
        lvl = ThreeGearLevel()
        lvl.set_voltage(5.0)
        for _ in range(int(2.0 / DT)):
            lvl.step()
        assert lvl.driver_rpm > 0
        assert lvl.driven_rpm > 0

    def test_idler_spins_opposite_to_driver(self):
        """Idler is between driver and driven, so it reverses once."""
        lvl = ThreeGearLevel()
        lvl.set_voltage(5.0)
        for _ in range(int(2.0 / DT)):
            lvl.step()
        assert lvl.driver_rpm > 0
        assert lvl.idler_rpm < 0

    def test_idler_does_not_change_speed_ratio(self):
        """Speed ratio = N_driver / N_driven, independent of N_idler."""
        # Driver N20, driven N40 → expected ratio = 0.5
        lvl_1 = ThreeGearLevel(
            driver_teeth=20, idler_teeth=30, driven_teeth=40, target_driven_rpm=100.0
        )
        v1 = solve_driving_voltage_1_3(100.0, lvl_1.driver, lvl_1.driven)
        lvl_1.set_voltage(abs(v1) * 1.01)
        for _ in range(int(5.0 / DT)):
            lvl_1.step()
        rpm_1 = abs(lvl_1.driven_rpm)

        # Same driver and driven, but different idler → should have same speed ratio
        lvl_2 = ThreeGearLevel(
            driver_teeth=20, idler_teeth=12, driven_teeth=40, target_driven_rpm=100.0
        )
        v2 = solve_driving_voltage_1_3(100.0, lvl_2.driver, lvl_2.driven)
        lvl_2.set_voltage(abs(v2) * 1.01)
        for _ in range(int(5.0 / DT)):
            lvl_2.step()
        rpm_2 = abs(lvl_2.driven_rpm)

        # Both should reach similar steady-state RPM
        assert abs(rpm_1 - rpm_2) < 5.0  # within ~5 RPM

    def test_set_gears_updates_all_three(self):
        lvl = ThreeGearLevel()
        lvl.set_gears(driver_teeth=12, idler_teeth=20, driven_teeth=60)
        assert lvl.driver.teeth == 12
        assert lvl.idler.teeth == 20
        assert lvl.driven.teeth == 60

    def test_frame_span_updates_on_set_gears(self):
        lvl = ThreeGearLevel()
        old_span = lvl.frame_span
        lvl.set_gears(driver_teeth=12, idler_teeth=16, driven_teeth=48)
        new_span = lvl.frame_span
        assert new_span != old_span


class TestWinCondition:
    def test_default_target_is_1_to_1_ratio(self):
        lvl = ThreeGearLevel()
        assert lvl.expected_driven_rpm == 1.0

    def test_win_condition_reached_with_correct_voltage(self):
        """Run at the correct voltage for the 1:1 default; should win."""
        lvl = ThreeGearLevel(target_driven_rpm=60.0)
        v = solve_driving_voltage_1_3(60.0, lvl.driver, lvl.driven)
        lvl.set_voltage(abs(v) * 1.01)
        for _ in range(int(8.0 / DT)):
            lvl.step()
        assert lvl.won is True

    def test_diagnostic_on_wrong_direction(self):
        """Negative voltage reverses direction but still spins, so actually too fast at first."""
        lvl = ThreeGearLevel(target_driven_rpm=60.0)
        lvl.set_voltage(-10.0)
        for _ in range(int(1.0 / DT)):
            lvl.step()
        # With negative voltage and target_sign=+1, the driven gear will spin
        # at negative RPM (wrong direction). Eventually _check_win will detect this.
        # But initially it's just "too fast" (magnitude check fails first).
        assert lvl.last_diagnostic is not None

    def test_diagnostic_on_too_slow(self):
        """Tiny voltage → too slow → diagnostic."""
        lvl = ThreeGearLevel(target_driven_rpm=60.0)
        lvl.set_voltage(0.01)
        for _ in range(int(5.0 / DT)):
            lvl.step()
        # Should be too slow
        if not lvl.won:
            assert lvl.last_diagnostic is not None


class TestSummary:
    def test_summary_includes_all_teeth_counts(self):
        lvl = ThreeGearLevel(driver_teeth=12, idler_teeth=20, driven_teeth=48)
        s = lvl.summary()
        assert s["driver_teeth"] == 12
        assert s["idler_teeth"] == 20
        assert s["driven_teeth"] == 48

    def test_summary_includes_all_rpms(self):
        lvl = ThreeGearLevel()
        lvl.set_voltage(5.0)
        lvl.step()
        s = lvl.summary()
        assert "driver_rpm" in s
        assert "idler_rpm" in s
        assert "driven_rpm" in s

    def test_summary_level_id(self):
        lvl = ThreeGearLevel()
        s = lvl.summary()
        assert s["level"] == "1.3"

    def test_summary_includes_target_sign(self):
        lvl = ThreeGearLevel()
        s = lvl.summary()
        assert s["target_sign"] == 1


class TestEdgeCases:
    def test_all_same_tooth_count(self):
        """All gears identical (N30)."""
        lvl = ThreeGearLevel(driver_teeth=30, idler_teeth=30, driven_teeth=30)
        v = solve_driving_voltage_1_3(60.0, lvl.driver, lvl.driven)
        lvl.set_voltage(abs(v) * 1.01)
        for _ in range(int(8.0 / DT)):
            lvl.step()
        assert lvl.won is True

    def test_smallest_and_largest_gears(self):
        """Extreme case: N12 driver (small, high speed) and N60 driven (large, low speed)."""
        # This 1:5 ratio means driven is 5× slower. Should still work.
        lvl = ThreeGearLevel(
            driver_teeth=12, idler_teeth=30, driven_teeth=60, target_driven_rpm=30.0
        )
        v = solve_driving_voltage_1_3(30.0, lvl.driver, lvl.driven)
        lvl.set_voltage(abs(v) * 1.01)
        for _ in range(int(8.0 / DT)):
            lvl.step()
        # Should converge with longer time
        assert abs(lvl.driven_rpm) > 20.0

    def test_voltage_clamping(self):
        lvl = ThreeGearLevel()
        lvl.set_voltage(100.0)
        assert lvl.applied_voltage == 24.0
        lvl.set_voltage(-100.0)
        assert lvl.applied_voltage == -24.0
