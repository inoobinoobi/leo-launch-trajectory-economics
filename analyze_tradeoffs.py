import os
import sys
import numpy as np
import pandas as pd
from openai import OpenAI

MODEL = "anthropic/claude-sonnet-4.6"
MAX_BUDGET_INR = 70.0
MAX_OUT_TOKENS = 2200

# Live AICredits INR catalog rates per 1M tokens for anthropic/claude-sonnet-4.6
INPUT_RATE_INR_PER_M = 294.57
OUTPUT_RATE_INR_PER_M = 1472.84

SYSTEM_PROMPT = """You are a Principal Aerospace Systems Engineer & Launch Economist writing a Systems Trade-Study Memo for a TUM Aerospace / Management & Data Science portfolio.

GOVERNING MODEL SPEC (use these exact parameters; do not invent others):
- 2-stage 2D spherical-Earth RK45 ascent; exponential atmosphere (H = 8.5 km); altitude-decaying wind shear.
- LEO Insertion Criteria: h >= 180 km AND v >= 7,750 m/s. Structural Limit: Max-Q <= 35.0 kPa.
- Mission Cost Model: Total Cost (€) = €4,200,000 fixed + €2.40/kg * (stage1_fuel_kg + stage2_fuel_kg).
- 2026 Market Benchmarks: SpaceX Transporter rideshare = $7,000/kg (~€6,500/kg, 50 kg min); Rocket Lab Electron dedicated small launch = ~$9.2M (~$25k-$30k/kg).

TASK & TOKEN BUDGET (~1,350 words total; cite exact numbers from the tables):
1. **Executive Summary & Optimal Operating Point (~200 words):** State overall feasibility rate, Pareto-optimal vehicle config, and minimum €/kg achieved.
2. **Ascent Physics & Regime Cliff Analysis (~400 words):** Explain the Payload × Pitch interaction matrix, gravity-turn losses vs. aerodynamic Max-Q overload, and wind shear sensitivity.
3. **Commercial Pricing & Risk-Adjusted Unit Economics (~400 words):** Compare our feasible €/kg cost against 2026 rideshare ($7,000/kg) and dedicated small-sat launchers (~$25k-$30k/kg). Recommend an optimal commercial price tier balancing margin against wind-induced failure risk.
4. **Surrogate Modeling & Control Recommendations (~350 words):** Explain why single-stage regression degrades across the ground-impact crash discontinuity (R² = 0.994 altitude vs. 0.80 velocity) and propose a 2-stage classifier-regressor + closed-loop pitch guidance upgrade."""


def df_to_markdown(df: pd.DataFrame) -> str:
    """Convert any DataFrame or crosstab into a clean Markdown table without tabulate."""
    df_reset = df.reset_index()
    df_reset.columns.name = None
    headers = [str(col) for col in df_reset.columns]
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in df_reset.itertuples(index=False):
        lines.append("| " + " | ".join(str(val) for val in row) + " |")
    return "\n".join(lines)


def compute_engineering_and_financial_summary(csv_path: str = "monte_carlo_launches.csv") -> str:
    """Aggregate deterministic sensitivity tables from the 5,000 Monte Carlo trajectories."""
    if not os.path.exists(csv_path):
        sys.exit(f"Error: '{csv_path}' not found in {os.getcwd()}")

    df = pd.read_csv(csv_path)
    df["orbit_achieved"] = df["orbit_achieved"].astype(int)
    df["total_cost_eur"] = (df["stage1_fuel_kg"] + df["stage2_fuel_kg"]) * 2.40 + 4_200_000.0
    df["cost_per_kg_eur"] = np.where(
        df["orbit_achieved"] == 1, df["total_cost_eur"] / df["payload_mass_kg"], np.nan
    )
    df["max_q_ok"] = df["max_q_kpa"] <= 35.0
    df["mission_valid"] = (df["orbit_achieved"] == 1) & df["max_q_ok"]

    df["payload_bin"] = pd.cut(
        df["payload_mass_kg"],
        bins=[200.0, 500.0, 800.0, 1100.0, 1400.0, 1800.0],
        labels=["200-500 kg", "500-800 kg", "800-1100 kg", "1100-1400 kg", "1400-1800 kg"],
        include_lowest=True,
    )
    df["pitch_bin"] = pd.cut(
        df["pitch_kick_deg"],
        bins=[2.0, 4.5, 7.0, 9.5, 12.0],
        labels=["2.0-4.5° (Steep)", "4.5-7.0° (Nominal)", "7.0-9.5° (Aggressive)", "9.5-12.0° (Shallow)"],
        include_lowest=True,
    )

    payload_grouped = df.groupby("payload_bin", observed=False).agg(
        runs=("orbit_achieved", "count"),
        leo_ok_pct=("orbit_achieved", lambda s: f"{s.mean() * 100:.1f}%"),
        valid_maxq_pct=("mission_valid", lambda s: f"{s.mean() * 100:.1f}%"),
        mean_max_q_kpa=("max_q_kpa", lambda s: f"{s.mean():.2f}"),
        median_cost_per_kg=("cost_per_kg_eur", lambda s: f"€{s.median():,.0f}" if s.notna().any() else "N/A"),
    )

    # 2D Interaction matrix: Joint Feasibility (LEO + Max-Q <= 35 kPa) across Payload x Pitch
    interaction_ct = pd.crosstab(
        df["payload_bin"],
        df["pitch_bin"],
        values=df["mission_valid"],
        aggfunc=lambda s: f"{s.mean() * 100:.0f}%" if len(s) > 0 else "N/A",
        dropna=False,
    )

    valid_df = df[df["mission_valid"]].copy()
    if valid_df.empty:
        valid_df = df[df["orbit_achieved"] == 1].copy()
    if valid_df.empty:
        sys.exit("Error: No successful LEO trajectories found in dataset.")
    best_row = valid_df.loc[valid_df["cost_per_kg_eur"].idxmin()]

    economics_lines = []
    for price in [6500, 8000, 9500, 11000]:
        rev = np.where(df["mission_valid"], df["payload_mass_kg"] * price, 0.0)
        net = rev - df["total_cost_eur"]
        economics_lines.append(
            f"- €{price:,}/kg: Expected Profit = €{net.mean():,.0f}/launch | "
            f"Profitable Runs = {(net > 0).mean() * 100:.1f}%"
        )

    return f"""### GLOBAL METRICS (N = {len(df):,} Runs)
- LEO Insertion Rate: {df['orbit_achieved'].mean() * 100:.1f}% | Max-Q <= 35 kPa Rate: {df['max_q_ok'].mean() * 100:.1f}% | Jointly Valid: {df['mission_valid'].mean() * 100:.1f}%
- Correlations with LEO Success -> Payload: {df['payload_mass_kg'].corr(df['orbit_achieved']):.3f} | Pitch Kick: {df['pitch_kick_deg'].corr(df['orbit_achieved']):.3f} | Wind: {df['wind_speed_mps'].corr(df['orbit_achieved']):.3f}

### PAYLOAD MASS SENSITIVITY
{df_to_markdown(payload_grouped)}

### 2D INTERACTION: JOINT FEASIBILITY % (PAYLOAD MASS x PITCH KICK)
{df_to_markdown(interaction_ct)}

### PARETO-OPTIMAL FEASIBLE RUN (Lowest €/kg with LEO + Max-Q <= 35 kPa)
- Payload: {best_row['payload_mass_kg']:.1f} kg | Pitch Kick: {best_row['pitch_kick_deg']:.2f}° | Wind: {best_row['wind_speed_mps']:.1f} m/s
- Propellant (S1 / S2): {best_row['stage1_fuel_kg']:.0f} kg / {best_row['stage2_fuel_kg']:.0f} kg
- Final Orbit: {best_row['final_alt_km']:.1f} km @ {best_row['final_speed_mps']:.1f} m/s | Max-Q: {best_row['max_q_kpa']:.2f} kPa
- Minimum Unit Cost: €{best_row['cost_per_kg_eur']:,.2f}/kg (Total Mission Cost: €{best_row['total_cost_eur']:,.0f})

### EXPECTED COMMERCIAL VALUE UNDER WIND & TRAJECTORY UNCERTAINTY
{chr(10).join(economics_lines)}"""


def generate_trade_study_memo() -> None:
    stats_report = compute_engineering_and_financial_summary()

    # Pre-flight worst-case budget check before spending a single rupee
    est_in_tokens = int((len(SYSTEM_PROMPT) + len(stats_report)) / 3.2) + 120
    worst_case_inr = (
        (est_in_tokens / 1_000_000) * INPUT_RATE_INR_PER_M
        + (MAX_OUT_TOKENS / 1_000_000) * OUTPUT_RATE_INR_PER_M
    )
    print(f"Pre-flight check: ~{est_in_tokens:,} input tok | Hard output cap: {MAX_OUT_TOKENS:,} tok")
    print(f"Maximum possible cost: ₹{worst_case_inr:.2f} (Strict cap: ₹{MAX_BUDGET_INR:.2f})")

    if worst_case_inr > MAX_BUDGET_INR:
        sys.exit(f"Aborted: Worst-case cost ₹{worst_case_inr:.2f} exceeds ₹{MAX_BUDGET_INR:.2f} limit.")

    api_key = os.getenv("AICREDITS_API_KEY", "").strip()
    if not api_key:
        api_key = input("Paste your AICredits API key (never saved to disk): ").strip()
    if not api_key:
        sys.exit("Error: No API key provided.")

    client = OpenAI(base_url="https://api.aicredits.in/v1", api_key=api_key)
    print("Generating Systems Trade-Study Memo with Claude Sonnet 4.6...")

    resp = client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        max_tokens=MAX_OUT_TOKENS,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": stats_report},
        ],
    )

    memo_text = resp.choices[0].message.content or ""
    usage = getattr(resp, "usage", None)
    in_tok = getattr(usage, "prompt_tokens", 0) or 0
    out_tok = getattr(usage, "completion_tokens", 0) or 0
    actual_inr = (in_tok / 1_000_000) * INPUT_RATE_INR_PER_M + (out_tok / 1_000_000) * OUTPUT_RATE_INR_PER_M

    full_doc = (
        "# Systems Engineering & Payload Economics Trade-Study Memo\n\n"
        "*Coupled 2D RK45 Monte Carlo Sensitivity Synthesis (N = 5,000)*\n\n"
        + memo_text
        + "\n\n---\n\n## Appendix: Monte Carlo Sensitivity Matrices\n\n"
        + stats_report
    )

    with open("TRADE_STUDY_MEMO.md", "w", encoding="utf-8") as f:
        f.write(full_doc)

    print(f"\nSaved TRADE_STUDY_MEMO.md! Actual tokens: {in_tok:,} in / {out_tok:,} out | Actual cost: ₹{actual_inr:.2f}")


if __name__ == "__main__":
    generate_trade_study_memo()