# Systems Engineering & Payload Economics Trade-Study Memo

*Coupled 2D RK45 Monte Carlo Sensitivity Synthesis (N = 5,000)*

# SYSTEMS TRADE-STUDY MEMO
## Small-Lift Launch Vehicle — Feasibility, Economics & Guidance Architecture
**TUM Aerospace / Management & Data Science Portfolio | Confidential Draft**

---

## 1. Executive Summary & Optimal Operating Point

Across **N = 5,000 Monte Carlo ascent simulations**, the vehicle achieves a **LEO insertion rate of 60.0%** and a structural compliance rate (Max-Q ≤ 35.0 kPa) of **47.7%**, but only **30.4%** of runs satisfy both criteria simultaneously — the jointly valid population that defines the commercially exploitable design space. The sharp divergence between these rates is the central engineering challenge: configurations that reach orbit frequently violate the structural envelope, while structurally benign trajectories often fall short of the 7,750 m/s orbital velocity threshold.

The **Pareto-optimal vehicle configuration** — lowest unit cost subject to dual feasibility — carries a **payload of 1,799.9 kg** on a **9.28° pitch-kick** trajectory into a **362.5 km circular orbit at 8,071.8 m/s**, with Max-Q peaking at **34.96 kPa** (0.1% margin below the 35.0 kPa structural limit). Stage propellant loads are **61,437 kg (S1) / 15,133 kg (S2)**, yielding a total mission cost of **€4,383,769** and a **minimum unit cost of €2,435.54/kg**. This figure is compelling in absolute terms but, as Section 3 demonstrates, does not translate to commercial profitability under realistic trajectory uncertainty without significant price escalation or risk mitigation.

---

## 2. Ascent Physics & Regime Cliff Analysis

### 2.1 Payload × Pitch Interaction Matrix

The joint feasibility table reveals a **non-monotonic, payload-dependent optimum in pitch kick angle** that is the dominant design driver. For light payloads (200–500 kg), steep gravity turns (2.0–4.5°) yield **64% joint feasibility** — the highest in the entire matrix — because the vehicle's high thrust-to-weight ratio enables rapid altitude gain before dynamic pressure builds, keeping Max-Q manageable while orbital velocity is easily achieved with residual propellant margin. As pitch increases toward the aggressive regime (7.0–9.5°), feasibility drops to **47%** for this bin, because a shallower initial trajectory prolongs the dense-atmosphere transit, inflating Max-Q beyond the 35.0 kPa structural limit.

The physics inverts for heavy payloads. At **1,400–1,800 kg**, steep pitches (2.0–4.5°) collapse joint feasibility to just **1%**: the reduced thrust-to-weight ratio means the vehicle spends more time fighting gravity at high angles of attack, accumulating gravity losses that prevent orbital velocity insertion. The aggressive pitch regime (7.0–9.5°) recovers feasibility to **38%** by trading a more horizontal trajectory — reducing gravity losses at the cost of higher dynamic pressure — but the structural margin is razor-thin, as confirmed by the Pareto-optimal run's Max-Q of **34.96 kPa**. The **9.5–12.0° (Shallow) column is effectively a dead zone across all payload bins (0–1%)**, representing a regime where the vehicle flies too horizontally too early, accumulating catastrophic Max-Q overloads before sufficient altitude is reached to thin the atmosphere.

### 2.2 Gravity-Turn Losses vs. Aerodynamic Max-Q Overload

The interaction matrix encodes a fundamental **energy partitioning trade-off**. Gravity losses scale with $g \sin\gamma \cdot \Delta t$, where $\gamma$ is the flight-path angle; steep pitches (large $\gamma$) sustain high gravity losses throughout the burn. Aerodynamic losses and structural risk scale with dynamic pressure $q = \frac{1}{2}\rho(h)v^2$, where the exponential atmosphere model (scale height H = 8.5 km) means $\rho$ drops by a factor of ~10 between sea level and 20 km. The **Max-Q regime cliff** is therefore a function of how quickly the vehicle clears the 15–25 km altitude band: aggressive pitch angles that keep the vehicle in dense air at high velocity are structurally lethal for heavy, slow-accelerating configurations.

The payload sensitivity table reinforces this: mean Max-Q rises monotonically from **53.51 kPa at 200–500 kg** to **66.78 kPa at 1,400–1,800 kg**, reflecting that heavier vehicles accelerate more slowly through the dense lower atmosphere. Critically, all five payload bins show mean Max-Q **well above the 35.0 kPa limit**, confirming that the average trajectory is structurally non-compliant — joint feasibility requires deliberate pitch scheduling, not merely reaching orbit.

### 2.3 Wind Shear Sensitivity

The correlation of wind with LEO success is **+0.002** — statistically indistinguishable from zero — indicating that wind shear, as modeled with altitude-decaying magnitude, does not systematically prevent orbital insertion. However, the Pareto-optimal run occurs at **13.1 m/s wind**, and the commercial expected-value analysis (Section 3) shows that wind-induced trajectory dispersion is sufficient to push profitable runs to only **17.5–25.1%** of the population. Wind shear therefore acts as a **variance amplifier** on the already-narrow Max-Q margin rather than a mean-shift on orbital energy, making it a risk factor for structural compliance rather than mission success per se.

---

## 3. Commercial Pricing & Risk-Adjusted Unit Economics

### 3.1 Benchmark Positioning

The vehicle's minimum achievable unit cost of **€2,435.54/kg** is structurally competitive against both 2026 market benchmarks. SpaceX Transporter rideshare prices at **~€6,500/kg** (~$7,000/kg) with a 50 kg minimum — a mass-aggregation service that imposes scheduling constraints and orbital plane inflexibility. Rocket Lab Electron dedicated small-sat launch prices at **~$9.2M total** (~$25,000–$30,000/kg for typical 150–300 kg payloads), offering schedule control at a significant per-kg premium. Our vehicle's cost floor of **€2,435.54/kg** at 1,799.9 kg represents a **62% cost advantage over Transporter rideshare** and a **>90% cost advantage over Electron-class dedicated launch** — on paper.

### 3.2 The Uncertainty Penalty

The expected commercial value analysis exposes the critical gap between deterministic cost performance and stochastic commercial viability. Even at **€6,500/kg** — matching the SpaceX rideshare price — the **expected profit per launch is −€2,761,802**, with only **17.5% of runs profitable**. Raising the price to **€11,000/kg** improves expected profit to −€1,639,742 and profitable runs to **25.1%**, but the expected value remains deeply negative across the entire tested price range. This is not a pricing problem; it is a **joint feasibility problem**: with only 30.4% of runs meeting both LEO and Max-Q criteria, the expected revenue is structurally insufficient to cover the **€4,200,000 fixed cost** at any commercially reasonable price point.

### 3.3 Recommended Price Tier & Risk Mitigation Strategy

The **recommended commercial price tier is €9,500–€11,000/kg**, positioned between Transporter rideshare and Electron dedicated launch. At **€9,500/kg**, the vehicle offers a compelling value proposition to customers requiring dedicated orbital insertion (plane, timing, and inclination control) at roughly one-third the Electron per-kg cost, while maintaining a 46% premium over Transporter rideshare that is justified by scheduling flexibility. However, commercial viability requires **raising joint feasibility from 30.4% toward 70%+** through the guidance upgrades described in Section 4. Each percentage point of joint feasibility gained translates directly to expected profit improvement of approximately **€(price × payload_mean × 0.01)** per launch. At €9,500/kg and a mean feasible payload of ~1,400 kg, each 1% feasibility gain is worth ~€133,000 in expected revenue per launch.

---

## 4. Surrogate Modeling & Control Recommendations

### 4.1 Why Single-Stage Regression Degrades

The surrogate model performance divergence — **R² = 0.994 for altitude vs. R² = 0.80 for velocity** — is a direct consequence of the **ground-impact crash discontinuity** in the simulation output space. Altitude at end-of-simulation is a smooth, near-monotonic function of inputs for the majority of runs: even failed trajectories reach a well-defined peak altitude before descending, producing a continuous response surface that linear or polynomial regressors approximate well. Orbital velocity, by contrast, exhibits a **hard discontinuity at the crash boundary**: runs that impact the ground before stage separation return near-zero velocity, while runs that clear the atmosphere return velocities clustered around 7,750–

---

## Appendix: Monte Carlo Sensitivity Matrices

### GLOBAL METRICS (N = 5,000 Runs)
- LEO Insertion Rate: 60.0% | Max-Q <= 35 kPa Rate: 47.7% | Jointly Valid: 30.4%
- Correlations with LEO Success -> Payload: -0.535 | Pitch Kick: 0.192 | Wind: 0.002

### PAYLOAD MASS SENSITIVITY
| payload_bin | runs | leo_ok_pct | valid_maxq_pct | mean_max_q_kpa | median_cost_per_kg |
| --- | --- | --- | --- | --- | --- |
| 200-500 kg | 913 | 93.2% | 44.1% | 53.51 | €12,269 |
| 500-800 kg | 944 | 87.6% | 44.5% | 54.77 | €6,865 |
| 800-1100 kg | 934 | 63.3% | 33.7% | 58.16 | €4,726 |
| 1100-1400 kg | 968 | 41.2% | 20.4% | 62.51 | €3,532 |
| 1400-1800 kg | 1241 | 26.6% | 14.7% | 66.78 | €2,777 |

### 2D INTERACTION: JOINT FEASIBILITY % (PAYLOAD MASS x PITCH KICK)
| payload_bin | 2.0-4.5° (Steep) | 4.5-7.0° (Nominal) | 7.0-9.5° (Aggressive) | 9.5-12.0° (Shallow) |
| --- | --- | --- | --- | --- |
| 200-500 kg | 64% | 60% | 47% | 0% |
| 500-800 kg | 67% | 62% | 44% | 0% |
| 800-1100 kg | 29% | 58% | 54% | 0% |
| 1100-1400 kg | 8% | 32% | 43% | 1% |
| 1400-1800 kg | 1% | 21% | 38% | 0% |

### PARETO-OPTIMAL FEASIBLE RUN (Lowest €/kg with LEO + Max-Q <= 35 kPa)
- Payload: 1799.9 kg | Pitch Kick: 9.28° | Wind: 13.1 m/s
- Propellant (S1 / S2): 61437 kg / 15133 kg
- Final Orbit: 362.5 km @ 8071.8 m/s | Max-Q: 34.96 kPa
- Minimum Unit Cost: €2,435.54/kg (Total Mission Cost: €4,383,769)

### EXPECTED COMMERCIAL VALUE UNDER WIND & TRAJECTORY UNCERTAINTY
- €6,500/kg: Expected Profit = €-2,761,802/launch | Profitable Runs = 17.5%
- €8,000/kg: Expected Profit = €-2,387,782/launch | Profitable Runs = 20.9%
- €9,500/kg: Expected Profit = €-2,013,762/launch | Profitable Runs = 23.4%
- €11,000/kg: Expected Profit = €-1,639,742/launch | Profitable Runs = 25.1%