# 2-Stage Launch Vehicle Trajectory & Payload Economics Simulator

An aerospace ascent simulator and machine-learning surrogate dashboard coupling 2D spherical-Earth orbital mechanics with commercial Low Earth Orbit (LEO) unit economics.

## Architecture
1. **Physics Solver (physics_sim.py):** Integrates a 5-state gravity-turn ascent (x, h, vx, vh, m) across two stages using scipy.integrate.solve_ivp (RK45) with exponential atmospheric density ( = 8.5\text{ km}$), altitude-decaying wind shear, and terminal ground-impact detection.
2. **GPU Surrogate (	rain_surrogate.py):** Generates 5,000 Monte Carlo trajectories across pitch-kick, wind, propellant, and payload distributions, then trains a multi-output XGBRegressor (	ree_method="hist", device="cuda").
3. **Interactive Trade-Off App (pp.py):** Compares exact ODE integration against millisecond surrogate inference alongside structural Max-Q limits and launch profit margins (€/kg to LEO).

## Surrogate Benchmark (5,000 Monte Carlo Runs)
* **Final Altitude (^2 = 0.994$, MAE $= 16.3\text{ km}$):** Captures smooth orbital insertion sensitivity across payload and propellant variations.
* **Terminal Velocity (^2 = 0.80$) & Max-Q (^2 = 0.83$):** Exhibits sharp variance across the crash/re-entry regime boundary where failed trajectories terminate at ground impact.
