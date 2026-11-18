import numpy as np
from scipy.integrate import solve_ivp

# Physical constants
G0 = 9.80665              # Standard gravity (m/s^2)
MU = 3.986004418e14       # Earth gravitational parameter (m^3/s^2)
R_EARTH = 6_371_000.0     # Earth mean radius (m)
RHO_0 = 1.225             # Sea-level air density (kg/m^3)
H_SCALE = 8_500.0         # Atmospheric scale height (m)


def simulate_launch(
    pitch_kick_deg: float = 5.5,
    wind_speed_mps: float = 0.0,
    payload_mass_kg: float = 500.0,
    stage1_fuel_kg: float = 65_000.0,
    stage2_fuel_kg: float = 14_000.0,
) -> dict:
    """
    Simulate a 2-stage rocket ascent to Low Earth Orbit (LEO).
    State vector y = [downrange_x, altitude_h, vx, vh, mass]
    """
    # Vehicle structural & propulsion parameters
    m_dry1, thrust1, isp1 = 4_500.0, 1_250_000.0, 300.0
    m_dry2, thrust2, isp2 = 1_200.0, 180_000.0, 345.0
    cd, area = 0.35, 4.5  # Drag coefficient and frontal cross-section (m^2)

    mdot1 = thrust1 / (isp1 * G0)
    mdot2 = thrust2 / (isp2 * G0)
    t_burn1 = stage1_fuel_kg / mdot1
    t_burn2 = stage2_fuel_kg / mdot2

    def atmosphere_and_drag(h: float, vx: float, vh: float):
        h_clamped = max(0.0, h)
        rho = RHO_0 * np.exp(-h_clamped / H_SCALE)
        # Jet-stream wind decays exponentially above 10 km
        local_wind = wind_speed_mps * np.exp(-h_clamped / 10_000.0)
        v_rel_x = vx - local_wind
        v_rel_h = vh
        v_rel = np.hypot(v_rel_x, v_rel_h)
        q_dyn = 0.5 * rho * v_rel**2
        drag = q_dyn * cd * area
        if v_rel > 1e-6:
            dx = drag * (v_rel_x / v_rel)
            dh = drag * (v_rel_h / v_rel)
        else:
            dx, dh = 0.0, 0.0
        return q_dyn, dx, dh

    def pitch_angle_rad(h: float, vx: float, vh: float) -> float:
        # Vertical climb to clear launch tower (0 - 150 m)
        if h < 150.0:
            return np.pi / 2.0
        # Smooth pitch-over maneuver (150 m - 1500 m)
        if h < 1_500.0:
            frac = (h - 150.0) / 1_350.0
            return np.deg2rad(90.0 - frac * pitch_kick_deg)
        # Gravity turn: align thrust with velocity vector
        return np.arctan2(vh, max(vx, 1e-3))

    def make_ode(thrust: float, mdot: float):
        def ode(t: float, y: np.ndarray):
            x, h, vx, vh, m = y
            r = R_EARTH + max(0.0, h)
            g_local = MU / (r**2)
            _, drag_x, drag_h = atmosphere_and_drag(h, vx, vh)
            theta = pitch_angle_rad(h, vx, vh)

            ax = (thrust * np.cos(theta) - drag_x) / m - (vx * vh) / r
            ah = (thrust * np.sin(theta) - drag_h) / m - g_local + (vx**2) / r
            return [vx, vh, ax, ah, -mdot]

        return ode

    def hit_ground(t: float, y: np.ndarray) -> float:
        # Trigger only after rocket has lifted off above 5 m
        return y[1] if t > 2.0 else 10.0

    hit_ground.terminal = True
    hit_ground.direction = -1

    # --- Stage 1 Ascent ---
    m0 = m_dry1 + stage1_fuel_kg + m_dry2 + stage2_fuel_kg + payload_mass_kg
    y0 = [0.0, 0.0, 0.0, 0.0, m0]
    t_eval1 = np.linspace(0.0, t_burn1, 300)

    sol1 = solve_ivp(
        make_ode(thrust1, mdot1),
        (0.0, t_burn1),
        y0,
        t_eval=t_eval1,
        events=hit_ground,
        rtol=1e-7,
        atol=1e-9,
    )

    # Check if Stage 1 crashed before separation
    if sol1.status == 1:
        t_all = sol1.t
        y_all = sol1.y
    else:
        # --- Stage Separation & Stage 2 Ascent ---
        y_sep = sol1.y[:, -1].copy()
        y_sep[4] -= m_dry1  # Jettison Stage 1 empty mass
        t_eval2 = np.linspace(t_burn1, t_burn1 + t_burn2, 400)

        sol2 = solve_ivp(
            make_ode(thrust2, mdot2),
            (t_burn1, t_burn1 + t_burn2),
            y_sep,
            t_eval=t_eval2,
            events=hit_ground,
            rtol=1e-7,
            atol=1e-9,
        )
        t_all = np.concatenate([sol1.t, sol2.t[1:]])
        y_all = np.hstack([sol1.y, sol2.y[:, 1:]])

    # Compute Max-Q across trajectory
    q_history = [
        atmosphere_and_drag(y_all[1, i], y_all[2, i], y_all[3, i])[0]
        for i in range(y_all.shape[1])
    ]
    max_q_kpa = max(q_history) / 1000.0

    final_alt_km = y_all[1, -1] / 1000.0
    final_vx = y_all[2, -1]
    final_vh = y_all[3, -1]
    final_speed = np.hypot(final_vx, final_vh)

    # LEO insertion check (target: >= 180 km altitude, >= 7,750 m/s orbital speed)
    orbit_achieved = (final_alt_km >= 180.0) and (final_speed >= 7_750.0)

    # Economics model (EUR)
    propellant_cost = (stage1_fuel_kg + stage2_fuel_kg) * 2.40   # ~€2.40/kg RP-1/LOX blend
    hardware_cost = 4_200_000.0                                  # Expendable/partial-recovery amortized cost
    total_cost_eur = propellant_cost + hardware_cost
    cost_per_kg_eur = total_cost_eur / payload_mass_kg if orbit_achieved else np.nan

    return {
        "t": t_all,
        "x_km": y_all[0] / 1000.0,
        "alt_km": y_all[1] / 1000.0,
        "vx": y_all[2],
        "vh": y_all[3],
        "final_alt_km": final_alt_km,
        "final_speed_mps": final_speed,
        "max_q_kpa": max_q_kpa,
        "orbit_achieved": orbit_achieved,
        "total_cost_eur": total_cost_eur,
        "cost_per_kg_eur": cost_per_kg_eur,
    }


if __name__ == "__main__":
    res = simulate_launch(pitch_kick_deg=5.5, wind_speed_mps=-10.0, payload_mass_kg=500.0)
    print(f"Final Altitude : {res['final_alt_km']:.2f} km")
    print(f"Final Velocity : {res['final_speed_mps']:.1f} m/s")
    print(f"Max-Q          : {res['max_q_kpa']:.2f} kPa")
    print(f"LEO Achieved   : {res['orbit_achieved']}")
    print(f"Total Cost     : €{res['total_cost_eur']:,.0f}")
    if res["orbit_achieved"]:
        print(f"Cost / kg LEO  : €{res['cost_per_kg_eur']:,.2f}/kg")