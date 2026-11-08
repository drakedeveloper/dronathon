"""Explicit SI-unit models; parameters are simulation assumptions until calibrated.

References and limits: docs/PHYSICS_RESEARCH.md. These calculations augment the
Gazebo rigid-body/rotor simulation and do not replace its integration.
"""
from dataclasses import dataclass
import math
import numpy as np


def positive(value, name, allow_zero=False):
    if not math.isfinite(value) or (value < 0 if allow_zero else value <= 0):
        raise ValueError(f"{name} must be finite and {'nonnegative' if allow_zero else 'positive'}")
    return value


@dataclass(frozen=True)
class Vehicle:
    mass_kg: float = 1.52
    rotor_count: int = 4
    rotor_radius_m: float = 0.1
    thrust_coefficient: float = 8.54858e-6
    max_omega_rad_s: float = 800.0
    rho_kg_m3: float = 1.225
    gravity_m_s2: float = 9.80665
    profile_power_w: float = 24.0
    induced_efficiency: float = 0.65
    electronics_power_w: float = 12.0
    body_cd_area_m2: float = 0.045
    tip_speed_m_s: float = 80.0

    def __post_init__(self):
        for name, value in self.__dict__.items():
            positive(value, name)
        if not isinstance(self.rotor_count, int):
            raise ValueError("rotor_count must be an integer")
        if self.induced_efficiency > 1:
            raise ValueError("Efficiency cannot exceed 1")

    @property
    def disk_area_m2(self):
        return self.rotor_count * math.pi * self.rotor_radius_m**2

    @property
    def weight_n(self):
        return self.mass_kg * self.gravity_m_s2

    @property
    def max_thrust_n(self):
        return self.rotor_count * self.thrust_coefficient * self.max_omega_rad_s**2

    @property
    def hover_omega_rad_s(self):
        return math.sqrt(self.weight_n / (self.rotor_count * self.thrust_coefficient))

    @property
    def induced_hover_velocity_m_s(self):
        return math.sqrt(self.weight_n / (2 * self.rho_kg_m3 * self.disk_area_m2))

    def thrust_margin(self, tilt_rad=0.0):
        if not math.isfinite(tilt_rad) or abs(tilt_rad) >= math.pi / 2:
            return -math.inf
        return self.max_thrust_n * math.cos(tilt_rad) / self.weight_n - 1

    def drag_force(self, ground_velocity, wind_velocity):
        relative = np.asarray(ground_velocity, dtype=float) - np.asarray(wind_velocity, dtype=float)
        if relative.shape != (3,) or not np.all(np.isfinite(relative)):
            raise ValueError("Velocity and wind must be finite 3-vectors")
        return -0.5 * self.rho_kg_m3 * self.body_cd_area_m2 * np.linalg.norm(relative) * relative

    def power_w(self, airspeed_m_s, climb_m_s=0.0):
        """Rotary-wing profile/induced/parasitic model + positive climb work.

        Horizontal-flight structure follows Zeng et al.; our coefficients are
        declared defaults, not copied measurements of this particular airframe.
        No descent-energy credit or regenerative power is assumed.
        """
        v = positive(airspeed_m_s, "airspeed", allow_zero=True)
        if not math.isfinite(climb_m_s):
            raise ValueError("Non-finite climb speed")
        v0 = self.induced_hover_velocity_m_s
        q = v * v / (2 * v0 * v0)
        # Stable equivalent of sqrt(sqrt(1+q*q)-q).
        induced_factor = math.sqrt(1 / (math.sqrt(1 + q * q) + q))
        induced = self.weight_n * v0 / self.induced_efficiency * induced_factor
        profile = self.profile_power_w * (1 + 3 * v*v / self.tip_speed_m_s**2)
        parasitic = 0.5 * self.rho_kg_m3 * self.body_cd_area_m2 * v**3
        climb = self.weight_n * max(climb_m_s, 0) / self.induced_efficiency
        return profile + induced + parasitic + climb + self.electronics_power_w


@dataclass
class Battery:
    capacity_wh: float = 15.0
    remaining_wh: float | None = None

    def __post_init__(self):
        positive(self.capacity_wh, "capacity_wh")
        if self.remaining_wh is None:
            self.remaining_wh = self.capacity_wh
        if not math.isfinite(self.remaining_wh) or not 0 <= self.remaining_wh <= self.capacity_wh:
            raise ValueError("Remaining energy outside capacity")

    def consume(self, power_w, dt_sim_s):
        positive(power_w, "power_w", allow_zero=True)
        positive(dt_sim_s, "dt_sim_s", allow_zero=True)
        used = power_w * dt_sim_s / 3600
        self.remaining_wh = max(0.0, self.remaining_wh - used)
        return used


def segment_energy(vehicle, start, end, wind, airspeed=3.0, ground_speed_limit=2.0):
    """Energy/time for an airspeed-limited segment with crosswind feasibility.

    Airspeed is chosen to cancel crosswind and make progress along the segment.
    An infeasible segment returns infinities; there is no division by zero or
    clipped negative ground speed that would falsely make it reachable.
    """
    positive(airspeed, "airspeed")
    positive(ground_speed_limit, "ground_speed_limit")
    delta = np.asarray(end, float) - np.asarray(start, float)
    wind = np.asarray(wind, float)
    if delta.shape != (3,) or wind.shape != (3,) or not np.all(np.isfinite([delta, wind])):
        raise ValueError("Expected finite 3-vectors")
    distance = float(np.linalg.norm(delta))
    if distance < 1e-9:
        return 0.0, 0.0
    direction = delta / distance
    parallel = float(wind @ direction)
    crosswind2 = max(0.0, float(wind @ wind) - parallel**2)
    if crosswind2 >= airspeed**2:
        return math.inf, math.inf
    speed = min(ground_speed_limit, math.sqrt(airspeed**2 - crosswind2) + parallel)
    if speed <= 0.05:
        return math.inf, math.inf
    velocity = speed * direction
    actual_air = float(np.linalg.norm(velocity - wind))
    duration = distance / speed
    return vehicle.power_w(actual_air, velocity[2]) * duration / 3600, duration


def route_energy(vehicle, points, wind, uncertainty_m_s=0.0, **kwargs):
    """Worst result among nominal + 8 horizontal wind perturbations.

    This sampled envelope is not a formal bound over every possible wind field.
    """
    positive(uncertainty_m_s, "wind uncertainty", allow_zero=True)
    wind = np.asarray(wind, float)
    winds = [wind]
    if uncertainty_m_s:
        winds += [wind + uncertainty_m_s*np.array([math.cos(t), math.sin(t), 0])
                  for t in np.linspace(0, 2*math.pi, 8, endpoint=False)]
    estimates = []
    for candidate in winds:
        energy, duration = 0.0, 0.0
        for a, b in zip(points, points[1:]):
            e, t = segment_energy(vehicle, a, b, candidate, **kwargs)
            energy += e
            duration += t
        estimates.append((energy, duration))
    return max(estimates, key=lambda item: item[0])


def braking_distance(speed, deceleration, latency_s=0.15, localization_sigma_m=0.15, sigma_factor=3.0):
    positive(speed, "speed", allow_zero=True)
    positive(deceleration, "deceleration")
    positive(latency_s, "latency", allow_zero=True)
    positive(localization_sigma_m, "localization sigma", allow_zero=True)
    positive(sigma_factor, "sigma factor", allow_zero=True)
    return speed*latency_s + speed**2/(2*deceleration) + sigma_factor*localization_sigma_m


def smooth_segment(start, end, duration, t):
    """Quintic rest-to-rest time scaling: position, velocity, acceleration.

    This is minimum-jerk for a single unconstrained rest-to-rest segment; it is
    not a full minimum-snap route optimizer or a collision-free spline proof.
    """
    positive(duration, "duration")
    if not math.isfinite(t):
        raise ValueError("Non-finite time")
    s = float(np.clip(t / duration, 0, 1))
    delta = np.asarray(end, float)-np.asarray(start, float)
    blend = 10*s**3-15*s**4+6*s**5
    d1 = (30*s*s-60*s**3+30*s**4)/duration
    d2 = (60*s-180*s*s+120*s**3)/duration**2
    return np.asarray(start)+delta*blend, delta*d1, delta*d2


def predict_payload_offset(height_m, wind_xy, initial_velocity_xy=(0., 0.), mass_kg=0.15,
                           cd_area_m2=0.004, rho=1.225, dt=0.002):
    """RK4 point-mass drop with quadratic 3D drag and constant horizontal wind.

    Returns horizontal offset and flight time to z=0. No rotor downwash,
    turbulence, parachute or bouncing is modeled. Compare with physical drops
    before claiming accurate delivery; uncertainty margins still apply.
    """
    positive(height_m, "height", allow_zero=True)
    for name, value in (("mass", mass_kg), ("CdA", cd_area_m2), ("rho", rho), ("dt", dt)):
        positive(value, name)
    if dt > 0.05:
        raise ValueError("Payload integration step too large")
    wind = np.array([*wind_xy, 0.], float)
    state = np.array([0., 0., height_m, *initial_velocity_xy, 0.], float)
    if wind.shape != (3,) or state.shape != (6,) or not np.all(np.isfinite([*wind, *state])):
        raise ValueError("Invalid drop vectors")
    if height_m == 0:
        return np.zeros(2), 0.0
    def derivative(s):
        relative = s[3:] - wind
        drag = -0.5*rho*cd_area_m2*np.linalg.norm(relative)*relative/mass_kg
        return np.r_[s[3:], drag + [0., 0., -9.80665]]
    elapsed = 0.
    while state[2] > 0 and elapsed < 60:
        old = state.copy()
        k1 = derivative(state)
        k2 = derivative(state+dt*k1/2)
        k3 = derivative(state+dt*k2/2)
        k4 = derivative(state+dt*k3)
        state += dt*(k1+2*k2+2*k3+k4)/6
        elapsed += dt
        if state[2] <= 0:
            fraction = old[2]/(old[2]-state[2])
            state = old + fraction*(state-old)
            elapsed -= dt*(1-fraction)
    if state[2] > 0:
        raise ValueError("Payload did not reach ground in integration horizon")
    return state[:2], elapsed
