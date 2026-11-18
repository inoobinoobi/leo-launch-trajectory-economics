import time
import numpy as np
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import xgboost as xgb

from physics_sim import simulate_launch

st.set_page_config(
    page_title="LEO Launch Trajectory & Payload Economics",
    layout="wide",
)

FEATURE_COLS = [
    "pitch_kick_deg",
    "wind_speed_mps",
    "payload_mass_kg",
    "stage1_fuel_kg",
    "stage2_fuel_kg",
]


@st.cache_resource
def load_surrogate() -> xgb.XGBRegressor:
    model = xgb.XGBRegressor()
    model.load_model("rocket_surrogate.json")
    model.set_params(device="cpu")
    model.get_booster().set_param({"device": "cpu"})
    return model


@st.cache_data
def load_monte_carlo() -> pd.DataFrame:
    return pd.read_csv("monte_carlo_launches.csv")


model = load_surrogate()
mc_df = load_monte_carlo()

st.title("2-Stage Launch Vehicle Trajectory & Payload Economics")
st.caption(
    "Coupled SciPy RK45 Ascent Physics + GPU-Trained XGBoost Surrogate + Mission Unit Economics"
)

# ── Sidebar Controls ─────────────────────────────────────────────────────────
st.sidebar.header("Mission & Vehicle Parameters")

pitch_kick = st.sidebar.slider("Pitch Kick Angle (deg)", 2.0, 12.0, 5.5, 0.1)
wind_speed = st.sidebar.slider("Wind Speed (m/s, +tailwind / -headwind)", -35.0, 35.0, -10.0, 1.0)
payload_mass = st.sidebar.slider("Payload Mass (kg)", 200.0, 1800.0, 850.0, 25.0)
s1_fuel = st.sidebar.slider("Stage 1 Propellant (kg)", 55000.0, 70000.0, 65000.0, 500.0)
s2_fuel = st.sidebar.slider("Stage 2 Propellant (kg)", 11000.0, 16000.0, 14000.0, 250.0)

st.sidebar.divider()
st.sidebar.header("Commercial Pricing")
price_per_kg = st.sidebar.slider("Customer Launch Price (€/kg)", 4000, 16000, 9500, 250)
max_q_limit = st.sidebar.number_input("Structural Max-Q Limit (kPa)", value=35.0, step=1.0)

# ── Surrogate Inference vs. Exact ODE Solver ─────────────────────────────────
x_input = np.array(
    [[pitch_kick, wind_speed, payload_mass, s1_fuel, s2_fuel]], dtype=np.float32
)

t0 = time.perf_counter()
surrogate_pred = model.predict(x_input)[0]
surrogate_ms = (time.perf_counter() - t0) * 1000.0

t1 = time.perf_counter()
ode_res = simulate_launch(
    pitch_kick_deg=pitch_kick,
    wind_speed_mps=wind_speed,
    payload_mass_kg=payload_mass,
    stage1_fuel_kg=s1_fuel,
    stage2_fuel_kg=s2_fuel,
)
ode_ms = (time.perf_counter() - t1) * 1000.0

# ── Top KPI Row ──────────────────────────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Final Altitude (ODE vs Surrogate)",
    f"{ode_res['final_alt_km']:.1f} km",
    f"Surrogate: {surrogate_pred[0]:.1f} km",
)
c2.metric(
    "Final Velocity (ODE vs Surrogate)",
    f"{ode_res['final_speed_mps']:.0f} m/s",
    f"Surrogate: {surrogate_pred[1]:.0f} m/s",
)
c3.metric(
    "Max-Q Dynamic Pressure",
    f"{ode_res['max_q_kpa']:.2f} kPa",
    "WITHIN LIMIT" if ode_res["max_q_kpa"] <= max_q_limit else "STRUCTURAL OVERLOAD",
    delta_color="normal" if ode_res["max_q_kpa"] <= max_q_limit else "inverse",
)

revenue_eur = payload_mass * price_per_kg
profit_eur = revenue_eur - ode_res["total_cost_eur"] if ode_res["orbit_achieved"] else -ode_res["total_cost_eur"]

if ode_res["orbit_achieved"]:
    c4.metric(
        "Cost / kg to LEO",
        f"€{ode_res['cost_per_kg_eur']:,.0f}/kg",
        f"Net Profit: €{profit_eur:,.0f}",
    )
else:
    c4.metric(
        "Mission Status",
        "LEO FAILED",
        f"Loss: -€{ode_res['total_cost_eur']:,.0f}",
        delta_color="inverse",
    )

st.info(
    f"**Compute Speedup:** XGBoost surrogate ran in **{surrogate_ms:.2f} ms** vs. "
    f"SciPy ODE solver in **{ode_ms:.2f} ms** (**{ode_ms / max(surrogate_ms, 1e-3):.1f}x faster**)."
)

# ── Charts: Trajectory Profile & Monte Carlo Feasibility Envelope ────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("Ascent Trajectory Profile")
    fig1, ax1 = plt.subplots(figsize=(6.5, 4.3))
    ax1.plot(ode_res["x_km"], ode_res["alt_km"], color="#1f77b4", linewidth=2.2, label="Vehicle Trajectory")
    ax1.axhline(180.0, color="#2ca02c", linestyle="--", linewidth=1.3, label="Min LEO Altitude (180 km)")
    ax1.set_xlabel("Downrange Distance (km)")
    ax1.set_ylabel("Altitude (km)")
    ax1.set_title("2D Gravity-Turn Ascent")
    ax1.grid(True, alpha=0.3)
    ax1.legend()
    st.pyplot(fig1)

with col_right:
    st.subheader("5,000-Run Monte Carlo Design Envelope")
    fig2, ax2 = plt.subplots(figsize=(6.5, 4.3))
    success = mc_df[mc_df["orbit_achieved"] == 1]
    fail = mc_df[mc_df["orbit_achieved"] == 0]
    ax2.scatter(fail["payload_mass_kg"], fail["pitch_kick_deg"], s=8, alpha=0.35, color="#d62728", label="Failed LEO")
    ax2.scatter(success["payload_mass_kg"], success["pitch_kick_deg"], s=8, alpha=0.35, color="#2ca02c", label="Achieved LEO")
    ax2.scatter([payload_mass], [pitch_kick], s=180, marker="*", color="#ffbf00", edgecolor="black", zorder=5, label="Current Mission")
    ax2.set_xlabel("Payload Mass (kg)")
    ax2.set_ylabel("Pitch Kick Angle (deg)")
    ax2.set_title("Payload vs. Pitch Feasibility Boundary")
    ax2.grid(True, alpha=0.3)
    ax2.legend()
    st.pyplot(fig2)

# ── Engineering & Management Trade-Off Summary ───────────────────────────────
with st.expander("Engineering & Surrogate Error Analysis (Methodology Notes)"):
    st.markdown(
        """
        * **Physics Model:** Integrates a 5-state 2D spherical-Earth ascent (`x, h, vx, vh, m`) using `scipy.integrate.solve_ivp` (RK45) with exponential atmospheric density ($H = 8.5\\text{ km}$) and terminal ground-impact detection.
        * **Surrogate Behavior:** Trained on 5,000 Monte Carlo trajectories on an NVIDIA GTX 1650 (`hist` + `cuda`). Altitude achieves $R^2 = 0.994$, while terminal velocity ($R^2 = 0.80$) exhibits sharp variance across the crash/re-entry regime boundary.
        * **Management Trade-Off:** Increasing payload lowers unit launch cost (€/kg) until trajectory energy drops below the $7,750\\text{ m/s}$ orbital insertion threshold, creating a sharp cliff between maximum margin and total mission loss.
        """
    )