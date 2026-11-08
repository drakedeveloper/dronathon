import math
import numpy as np
import pytest
from skyforge.physics import Vehicle, Battery, segment_energy, route_energy, braking_distance, smooth_segment, predict_payload_offset


def test_hover_thrust_balances_weight_and_has_headroom():
    v = Vehicle()
    assert v.rotor_count*v.thrust_coefficient*v.hover_omega_rad_s**2 == pytest.approx(v.weight_n)
    assert v.hover_omega_rad_s < v.max_omega_rad_s
    assert v.thrust_margin() > 0
    assert v.thrust_margin(math.pi/2) < 0


def test_energy_uses_sim_time_and_never_goes_negative():
    b = Battery(1)
    b.consume(360, 5)
    assert b.remaining_wh == pytest.approx(0.5)
    b.consume(999, 0)
    assert b.remaining_wh == pytest.approx(0.5)
    b.consume(3600, 10)
    assert b.remaining_wh == 0
    with pytest.raises(ValueError):
        b.consume(1, -1)


def test_infeasible_headwind_and_crosswind_are_explicit():
    v = Vehicle()
    assert math.isinf(segment_energy(v, [0,0,0], [10,0,0], [-4,0,0])[0])
    assert math.isinf(segment_energy(v, [0,0,0], [10,0,0], [0,4,0])[0])
    assert segment_energy(v, [0,0,0], [0,0,0], [99,0,0]) == (0,0)


def test_wind_uncertainty_is_at_least_nominal_route_estimate():
    v = Vehicle()
    p = [[0,0,5], [10,0,5], [10,8,5]]
    nominal = route_energy(v, p, [0.5,0,0])[0]
    assert route_energy(v, p, [0.5,0,0], uncertainty_m_s=0.5)[0] >= nominal


def test_drag_opposes_relative_air_velocity():
    v = Vehicle()
    np.testing.assert_allclose(v.drag_force([2,0,0], [2,0,0]), [0,0,0])
    assert v.drag_force([2,0,0], [0,0,0])[0] < 0


def test_smooth_trajectory_has_zero_endpoint_velocity_and_acceleration():
    for t, expected in [(0, [0,0,0]), (2, [2,4,6])]:
        p, speed, acceleration = smooth_segment([0,0,0], [2,4,6], 2, t)
        np.testing.assert_allclose(p, expected)
        np.testing.assert_allclose(speed, [0,0,0], atol=1e-12)
        np.testing.assert_allclose(acceleration, [0,0,0], atol=1e-12)


def test_drop_symmetry_and_crosswind_drift():
    calm, t = predict_payload_offset(2, [0,0])
    np.testing.assert_allclose(calm, [0,0])
    assert t > math.sqrt(4/9.80665)
    right, _ = predict_payload_offset(2, [3,0])
    left, _ = predict_payload_offset(2, [-3,0])
    assert right[0] > 0
    np.testing.assert_allclose(right, -left, atol=1e-10)


def test_clearance_grows_with_speed_and_latency():
    assert braking_distance(2, 1, 0.2) > braking_distance(1, 1, 0.2)
    assert braking_distance(2, 1, 0.2) > braking_distance(2, 1, 0.1)
