"""Data-contract checks for a generated telemetry batch."""

from __future__ import annotations

import sys
from datetime import timedelta
from pathlib import Path

import pandas as pd

from generate_cmapss_sensor import BATCHES_DIR, LATE_INGEST_THRESHOLD, REFERENCE_DIR


def _read_reference(filename: str) -> pd.DataFrame:
    frame = pd.read_csv(REFERENCE_DIR / filename, skipinitialspace=True)
    frame.columns = frame.columns.str.strip()
    return frame


def _unique(frame: pd.DataFrame, column: str, name: str) -> None:
    if frame[column].isna().any() or frame[column].duplicated().any():
        raise ValueError(f"{name}.{column} must be non-null and unique")


def _foreign_key(child: pd.DataFrame, column: str, parent: pd.DataFrame, parent_column: str) -> None:
    missing = set(child[column].dropna()) - set(parent[parent_column].dropna())
    if missing:
        raise ValueError(f"Orphan {column}: {sorted(missing)[:10]}")


def validate_batch(batch_dir: str | Path) -> None:
    batch_dir = Path(batch_dir)
    aircraft = _read_reference("Aircraft Data Dictionary - aircraft_data .csv")
    engines = _read_reference("Aircraft Data Dictionary - engine_data.csv")
    pilots = _read_reference("Aircraft Data Dictionary - pilot_data.csv")
    airports = _read_reference("Aircraft Data Dictionary - airport_data.csv")
    flights = pd.read_csv(batch_dir / "flight_data.csv")
    sensors = pd.read_parquet(batch_dir / "engine_sensor_data.parquet")

    for frame, column, name in [(aircraft, "aircraft_id", "aircraft"), (engines, "engine_id", "engine"), (pilots, "pilot_id", "pilot"), (airports, "airport_code", "airport"), (flights, "flight_id", "flight"), (sensors, "event_id", "sensor")]:
        _unique(frame, column, name)
    for child, column, parent, parent_column in [(engines, "aircraft_id", aircraft, "aircraft_id"), (flights, "aircraft_id", aircraft, "aircraft_id"), (flights, "pilot_id", pilots, "pilot_id"), (flights, "copilot_id", pilots, "pilot_id"), (flights, "departure_airport", airports, "airport_code"), (flights, "arrival_airport", airports, "airport_code"), (sensors, "flight_id", flights, "flight_id"), (sensors, "engine_id", engines, "engine_id")]:
        _foreign_key(child, column, parent, parent_column)
    actual_engine_counts = engines.groupby("aircraft_id").size()
    declared_engine_counts = aircraft.set_index("aircraft_id")["engine_count"].reindex(actual_engine_counts.index)
    if not actual_engine_counts.equals(declared_engine_counts):
        raise ValueError("aircraft.engine_count does not match the engine master")

    active_aircraft = set(aircraft.loc[aircraft.status.eq("ACTIVE"), "aircraft_id"])
    if not set(flights.aircraft_id).issubset(active_aircraft):
        raise ValueError("A non-active aircraft was assigned a flight")
    if (flights.pilot_id == flights.copilot_id).any():
        raise ValueError("A flight has the same pilot and copilot")
    for pilot_id in set(flights.pilot_id) | set(flights.copilot_id):
        assigned = flights.loc[(flights.pilot_id == pilot_id) | (flights.copilot_id == pilot_id)].copy()
        assigned["_start"] = pd.to_datetime(assigned.actual_departure, utc=True, format="ISO8601")
        assigned["_end"] = pd.to_datetime(assigned.actual_arrival, utc=True, format="ISO8601")
        assigned = assigned.sort_values("_start")
        if (assigned["_start"].iloc[1:].to_numpy() < assigned["_end"].iloc[:-1].to_numpy()).any():
            raise ValueError(f"Pilot {pilot_id} has overlapping flights")
    flight_aircraft = flights.set_index("flight_id").aircraft_id
    engine_aircraft = engines.set_index("engine_id").aircraft_id
    if not sensors.apply(lambda row: flight_aircraft[row.flight_id] == row.aircraft_id == engine_aircraft[row.engine_id], axis=1).all():
        raise ValueError("Telemetry aircraft does not match its flight or engine")
    if sensors.duplicated(["flight_id", "engine_id", "sequence_no"]).any():
        raise ValueError("Duplicate telemetry sequence")

    event_time = pd.to_datetime(sensors.event_time, utc=True, format="ISO8601")
    ingest_time = pd.to_datetime(sensors.ingest_time, utc=True, format="ISO8601")
    bounds = flights.set_index("flight_id")
    start = pd.to_datetime(sensors.flight_id.map(bounds.actual_departure), utc=True, format="ISO8601")
    end = pd.to_datetime(sensors.flight_id.map(bounds.actual_arrival), utc=True, format="ISO8601")
    if not ((event_time > start) & (event_time < end)).all():
        raise ValueError("Sensor event lies outside its flight window")
    if not (ingest_time >= event_time).all():
        raise ValueError("Sensor ingest_time is before event_time")
    late = sensors.quality_flag.eq("LATE")
    if not ((ingest_time[late] - event_time[late]) > LATE_INGEST_THRESHOLD).all():
        raise ValueError("LATE rows do not exceed the late-ingest threshold")
    if not ((ingest_time[~late] - event_time[~late]) <= LATE_INGEST_THRESHOLD).all():
        raise ValueError("GOOD rows exceed the late-ingest threshold")
    if set(flights.flight_id) != set(sensors.flight_id):
        raise ValueError("Every generated flight must have telemetry")
    print(f"Validation passed: {len(flights):,} flights, {len(sensors):,} sensor rows, {int(late.sum()):,} late rows.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(f"Usage: python {Path(__file__).name} <batch-directory>")
    validate_batch(sys.argv[1])
