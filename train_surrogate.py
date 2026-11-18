import time
from concurrent.futures import ProcessPoolExecutor
import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import mean_absolute_error, r2_score
from sklearn.model_selection import train_test_split

from physics_sim import simulate_launch

N_SAMPLES = 5_000
FEATURE_COLS = [
    "pitch_kick_deg",
    "wind_speed_mps",
    "payload_mass_kg",
    "stage1_fuel_kg",
    "stage2_fuel_kg",
]
TARGET_COLS = ["final_alt_km", "final_speed_mps", "max_q_kpa"]


def _run_single_sim(params: np.ndarray) -> list[float]:
    pitch, wind, payload, s1_fuel, s2_fuel = params
    res = simulate_launch(
        pitch_kick_deg=float(pitch),
        wind_speed_mps=float(wind),
        payload_mass_kg=float(payload),
        stage1_fuel_kg=float(s1_fuel),
        stage2_fuel_kg=float(s2_fuel),
    )
    return [
        float(pitch),
        float(wind),
        float(payload),
        float(s1_fuel),
        float(s2_fuel),
        res["final_alt_km"],
        res["final_speed_mps"],
        res["max_q_kpa"],
        int(res["orbit_achieved"]),
    ]


def generate_dataset(n_samples: int = N_SAMPLES, seed: int = 42) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    samples = np.column_stack([
        rng.uniform(2.0, 12.0, n_samples),        # pitch_kick_deg
        rng.uniform(-35.0, 35.0, n_samples),      # wind_speed_mps
        rng.uniform(200.0, 1_800.0, n_samples),   # payload_mass_kg
        rng.uniform(55_000.0, 70_000.0, n_samples), # stage1_fuel_kg
        rng.uniform(11_000.0, 16_000.0, n_samples), # stage2_fuel_kg
    ])

    print(f"Running {n_samples:,} Monte Carlo physics simulations across CPU cores...")
    t0 = time.perf_counter()
    with ProcessPoolExecutor() as executor:
        rows = list(executor.map(_run_single_sim, samples, chunksize=50))
    elapsed = time.perf_counter() - t0
    print(f"Simulations completed in {elapsed:.1f} s ({n_samples / elapsed:.0f} runs/sec)")

    cols = FEATURE_COLS + TARGET_COLS + ["orbit_achieved"]
    df = pd.DataFrame(rows, columns=cols)
    df.to_csv("monte_carlo_launches.csv", index=False)
    print(f"Saved monte_carlo_launches.csv (LEO success rate: {df['orbit_achieved'].mean()*100:.1f}%)")
    return df


def train_gpu_surrogate(df: pd.DataFrame) -> None:
    X = df[FEATURE_COLS].to_numpy(dtype=np.float32)
    y = df[TARGET_COLS].to_numpy(dtype=np.float32)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.15, random_state=42
    )

    try:
        model = xgb.XGBRegressor(
            n_estimators=600,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.9,
            tree_method="hist",
            device="cuda",
            random_state=42,
        )
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        train_time = time.perf_counter() - t0
        print(f"\nTrained XGBoost surrogate on NVIDIA GTX 1650 (CUDA) in {train_time:.2f} s")
    except xgb.core.XGBoostError:
        print("\nCUDA device unavailable; falling back to multi-core CPU hist...")
        model = xgb.XGBRegressor(
            n_estimators=600,
            max_depth=7,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.9,
            tree_method="hist",
            device="cpu",
            random_state=42,
        )
        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        train_time = time.perf_counter() - t0
        print(f"Trained XGBoost surrogate on CPU in {train_time:.2f} s")

    # Benchmark inference speed & accuracy
    t_inf = time.perf_counter()
    preds = model.predict(X_test)
    inf_ms = (time.perf_counter() - t_inf) * 1000.0

    print(f"Surrogate inference time for {len(X_test)} trajectories: {inf_ms:.2f} ms")
    for idx, name in enumerate(TARGET_COLS):
        mae = mean_absolute_error(y_test[:, idx], preds[:, idx])
        r2 = r2_score(y_test[:, idx], preds[:, idx])
        print(f"  {name:<16} -> MAE: {mae:7.2f} | R²: {r2:.5f}")

    model.save_model("rocket_surrogate.json")
    print("\nExported weights to rocket_surrogate.json")


if __name__ == "__main__":
    dataset = generate_dataset()
    train_gpu_surrogate(dataset)