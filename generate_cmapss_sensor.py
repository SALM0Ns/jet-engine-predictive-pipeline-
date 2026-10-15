"""Relational mock-data factory for aircraft telemetry batches.

The factory never modifies reference data and never overwrites a previous run.
Each invocation writes a self-contained batch under ``data/processed/batches``.
"""

from __future__ import annotations

import json
import random
import shutil
import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parent
REFERENCE_DIR = PROJECT_ROOT / "data" / "reference"
BATCHES_DIR = PROJECT_ROOT / "data" / "processed" / "batches"
LATE_INGEST_THRESHOLD = timedelta(minutes=5)


def _read_reference(filename: str) -> pd.DataFrame:
    frame = pd.read_csv(REFERENCE_DIR / filename, skipinitialspace=True)
    frame.columns = frame.columns.str.strip()
    return frame


def _new_batch_id(now: datetime) -> str:
    return f"batch-{now.strftime('%Y%m%dT%H%M%SZ')}-{uuid.uuid4().hex[:8]}"


def generate_relational_mock_data(
    num_new_flights: int = 5_000,
    ticks_per_flight: int = 100,
    seed: int | None = None,
    batch_id: str | None = None,
    start_time: datetime | None = None,
) -> Path:
    """Generate a time-consistent, immutable telemetry batch and return its path."""
    if num_new_flights <= 0 or ticks_per_flight <= 0:
        raise ValueError("num_new_flights and ticks_per_flight must be positive")

    now = datetime.now(timezone.utc)
    start_time = start_time or now.replace(hour=0, minute=0, second=0, microsecond=0)
    if start_time.tzinfo is None:
        raise ValueError("start_time must include a timezone")
    batch_id = batch_id or _new_batch_id(now)
    if not batch_id.replace("-", "").replace("_", "").isalnum():
        raise ValueError("batch_id may contain only letters, numbers, hyphens and underscores")
    BATCHES_DIR.mkdir(parents=True, exist_ok=True)
    destination = BATCHES_DIR / batch_id
    if destination.exists():
        raise FileExistsError(f"Batch already exists: {destination}")

    rng = random.Random(seed)
    aircraft = _read_reference("Aircraft Data Dictionary - aircraft_data .csv")
    engines = _read_reference("Aircraft Data Dictionary - engine_data.csv")
    pilots = _read_reference("Aircraft Data Dictionary - pilot_data.csv")
    airports = _read_reference("Aircraft Data Dictionary - airport_data.csv")
    weather = _read_reference("Aircraft Data Dictionary - weather_data.csv")
    active_aircraft = aircraft.loc[aircraft["status"].eq("ACTIVE")].copy()
    if active_aircraft.empty or len(pilots) < 2 or len(airports) < 2:
        raise ValueError("Need active aircraft, two pilots, and two airports")

    engine_ids_by_aircraft = engines.groupby("aircraft_id")["engine_id"].agg(list).to_dict()
    active_aircraft = active_aircraft.loc[active_aircraft["aircraft_id"].isin(engine_ids_by_aircraft)]
    aircraft_by_id = active_aircraft.set_index("aircraft_id")
    engine_by_id = engines.set_index("engine_id")
    engine_state = {
        engine_id: {"flight_cycles": float(row.flight_cycles), "flight_hours": float(row.flight_hours), "wear": min(0.65, float(row.flight_hours) / 20_000)}
        for engine_id, row in engine_by_id.iterrows()
    }
    pilot_ids = pilots["pilot_id"].tolist()
    airport_codes = airports["airport_code"].tolist()
    weather_values = weather["weather_name"].tolist()
    weather_weights = weather["probability"].tolist()
    flights: list[dict] = []
    telemetry: list[dict] = []

    # Flights are serialized four hours apart. This guarantees that a pilot cannot
    # be assigned to overlapping flights while retaining varied flight durations.
    for number in range(1, num_new_flights + 1):
        flight_id = f"FLT_{batch_id}_{number:06d}"
        aircraft_id = rng.choice(active_aircraft["aircraft_id"].tolist())
        pilot_id = rng.choice(pilot_ids)
        copilot_id = rng.choice([value for value in pilot_ids if value != pilot_id])
        departure_airport = rng.choice(airport_codes)
        arrival_airport = rng.choice([code for code in airport_codes if code != departure_airport])
        weather_condition = rng.choices(weather_values, weights=weather_weights, k=1)[0]
        scheduled_departure = start_time + timedelta(hours=4 * (number - 1))
        actual_departure = scheduled_departure + timedelta(minutes=rng.randint(0, 10))
        duration = timedelta(minutes=rng.randint(100, 180))
        actual_arrival = actual_departure + duration
        created_at = now.isoformat().replace("+00:00", "Z")
        flights.append({
            "batch_id": batch_id, "flight_id": flight_id, "flight_no": f"MIL{rng.randint(10, 99)}{number:05d}",
            "aircraft_id": aircraft_id, "pilot_id": pilot_id, "copilot_id": copilot_id,
            "departure_airport": departure_airport, "arrival_airport": arrival_airport,
            "scheduled_departure": scheduled_departure.isoformat().replace("+00:00", "Z"),
            "actual_departure": actual_departure.isoformat().replace("+00:00", "Z"),
            "scheduled_arrival": (scheduled_departure + duration).isoformat().replace("+00:00", "Z"),
            "actual_arrival": actual_arrival.isoformat().replace("+00:00", "Z"),
            "flight_status": "COMPLETED", "weather_condition": weather_condition,
            "created_at": created_at, "updated_at": created_at,
        })
        spec = aircraft_by_id.loc[aircraft_id]
        for tick in range(1, ticks_per_flight + 1):
            phase = tick / (ticks_per_flight + 1)
            event_time = actual_departure + duration * phase
            climb_descent = min(phase / 0.18, 1, (1 - phase) / 0.18)
            altitude = int(max(0, float(spec.cruise_altitude_ft) * climb_descent))
            speed = max(0.0, float(spec.max_speed_knots) * (0.30 + 0.50 * climb_descent))
            for engine_id in engine_ids_by_aircraft[aircraft_id]:
                engine = engine_by_id.loc[engine_id]
                state = engine_state[engine_id]
                within_flight_wear = state["wear"] + phase * 0.002
                weather_impact = 30 if weather_condition == "Thunderstorm" else 0
                temperature = float(engine.max_temp_c) * (0.57 + within_flight_wear * 0.22) + weather_impact + rng.uniform(-4, 4)
                vibration = 8.0 + within_flight_wear * 22 + phase * 1.5 + rng.uniform(-0.4, 0.4)
                anomaly = temperature > float(engine.max_temp_c) * 0.75 or vibration > 18
                is_late = rng.random() < 0.01
                ingest_delay = timedelta(minutes=rng.randint(6, 60)) if is_late else timedelta(seconds=rng.randint(1, 90))
                telemetry.append({
                    "batch_id": batch_id, "event_id": f"EVT_{batch_id}_{len(telemetry) + 1:012d}",
                    "flight_id": flight_id, "aircraft_id": aircraft_id, "engine_id": engine_id,
                    "event_time": event_time.isoformat().replace("+00:00", "Z"),
                    "ingest_time": (event_time + ingest_delay).isoformat().replace("+00:00", "Z"),
                    "sequence_no": tick, "altitude_ft": altitude, "speed_knots": round(speed + rng.uniform(-12, 12), 1),
                    "engine_temp_c": round(temperature, 1), "engine_pressure_kpa": round(225 + rng.uniform(-5, 5), 1),
                    "fuel_flow_kg_h": round(1200 + speed * 1.15 + rng.uniform(-15, 15), 1), "vibration_hz": round(vibration, 2),
                    "rpm": int(float(engine.max_rpm) * (0.65 + climb_descent * 0.15) + rng.randint(-40, 40)),
                    "oil_temp_c": round(temperature * 0.15 + rng.uniform(-2, 2), 1), "oil_pressure_kpa": round(350 - phase * 20 + rng.uniform(-4, 4), 1),
                    "status": "WARNING" if anomaly else "OK", "quality_flag": "LATE" if is_late else "GOOD",
                    "is_anomaly": anomaly, "cumulative_degradation": round(within_flight_wear, 6), "source": "relational_factory_v3",
                })
        flight_hours = duration.total_seconds() / 3600
        for engine_id in engine_ids_by_aircraft[aircraft_id]:
            state = engine_state[engine_id]
            state["flight_cycles"] += 1
            state["flight_hours"] += flight_hours
            state["wear"] = min(0.95, state["wear"] + flight_hours / 15_000 + 0.0005)

    flight_frame = pd.DataFrame(flights)
    telemetry_frame = pd.DataFrame(telemetry)
    engine_snapshot = engines.copy()
    engine_snapshot["flight_cycles"] = engine_snapshot["engine_id"].map(lambda value: int(engine_state[value]["flight_cycles"]))
    engine_snapshot["flight_hours"] = engine_snapshot["engine_id"].map(lambda value: round(engine_state[value]["flight_hours"], 2))
    engine_snapshot["cumulative_degradation"] = engine_snapshot["engine_id"].map(lambda value: round(engine_state[value]["wear"], 6))
    engine_snapshot["updated_at"] = created_at

    temporary = Path(tempfile.mkdtemp(prefix=f".{batch_id}-", dir=BATCHES_DIR))
    try:
        flight_frame.to_csv(temporary / "flight_data.csv", index=False)
        telemetry_frame.to_parquet(temporary / "engine_sensor_data.parquet", index=False)
        engine_snapshot.to_csv(temporary / "engine_state_snapshot.csv", index=False)
        manifest = {
            "batch_id": batch_id, "created_at": created_at, "seed": seed,
            "flight_rows": len(flight_frame), "telemetry_rows": len(telemetry_frame),
            "ticks_per_flight": ticks_per_flight, "late_ingest_threshold_seconds": int(LATE_INGEST_THRESHOLD.total_seconds()),
            "files": ["flight_data.csv", "engine_sensor_data.parquet", "engine_state_snapshot.csv"],
        }
        (temporary / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        temporary.rename(destination)
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    return destination


if __name__ == "__main__":
    print(generate_relational_mock_data())
