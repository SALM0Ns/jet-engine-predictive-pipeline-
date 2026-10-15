# Jet Engine Predictive Pipeline

This repository is a relational aircraft telemetry data factory and validation pipeline.

Machine learning and mathematical prediction are intentionally out of scope for this stage. The current stage produces validated, immutable batches for future modeling.

## Current status

- Google Cloud Storage is the active cloud destination.
- Azure code has been removed from the active pipeline.
- Every run receives a unique batch ID and never overwrites an existing batch.
- Sensor event times are inside each flight window.
- Engine degradation, cycles, and hours accumulate across flights.
- Only ACTIVE aircraft are scheduled.
- LATE means an ingest delay greater than five minutes.

## Architecture

~~~text
data/reference/*.csv
        |
        v
generate_cmapss_sensor.py
        |
        v
data/processed/batches/<batch_id>/
  |-- manifest.json
  |-- flight_data.csv
  |-- engine_sensor_data.parquet
  `-- engine_state_snapshot.csv
        |
        |-- validate_data.py
        `-- upload_to_gcs.py
~~~

All files from one batch must be loaded together. Do not join telemetry from one batch with a different batch's flight or engine snapshot.

## Repository layout

~~~text
.
|-- main.py
|-- generate_cmapss_sensor.py
|-- validate_data.py
|-- upload_to_gcs.py
|-- requirements.txt
|-- Dockerfile
|-- DATA_LAYOUT.md
|-- README.md
|-- .gitignore
|-- .vscode/settings.json
|-- data/reference/
|-- data/processed/batches/
|-- data/legacy/
|-- data/Raw/
|-- data/refer/
|-- query-data.ipynb
`-- test_query.ipynb
~~~

The repository was scanned including hidden files. The ignore file excludes service-account JSON patterns, Python caches, generated batches, nested raw output, and .DS_Store. The VS Code settings file contains only local Python environment preferences. Never commit credentials even if a filename is not ignored.

The working tree currently contains a root-level file named flight-data-sim-327a53426d45.json. It matches the credential ignore rule, but it should still be treated as sensitive: rotate or revoke its credentials and keep the replacement outside the repository before sharing or deploying.

The old nested output under data/Raw/data/Raw/ was moved to data/legacy/nested_raw_output/. Legacy CSV and Parquet files are retained for reference only and are not current pipeline inputs.

## Data model

| Dataset | Primary key | Important relationships |
|---|---|---|
| Aircraft reference | aircraft_id | Parent of engines and flights |
| Engine reference | engine_id | aircraft_id -> aircraft.aircraft_id |
| Pilot reference | pilot_id | Parent of flight pilot and copilot |
| Airport reference | airport_code | Parent of departure and arrival airports |
| Flight batch | flight_id | References aircraft, pilots, and airports |
| Engine telemetry batch | event_id | References flight, aircraft, and engine |
| Engine state snapshot | engine_id | Post-batch cycles, hours, and degradation |

Airport values in flight data are codes such as KLSV, not display names, so they join directly to the airport reference table.

## Generated batch files

### flight_data.csv

Contains batch_id, flight_id, flight_no, aircraft/pilot/copilot IDs, airport codes, scheduled and actual timestamps, flight_status, weather_condition, and audit timestamps.

### engine_sensor_data.parquet

Contains batch_id, event_id, flight_id, aircraft_id, engine_id, event_time, ingest_time, sequence_no, sensor measurements, status, quality_flag, is_anomaly, cumulative_degradation, and source.

Time rules:

- actual_departure < event_time < actual_arrival
- ingest_time >= event_time
- GOOD means delay at most five minutes
- LATE means delay greater than five minutes

### engine_state_snapshot.csv

Contains the engine state after the batch. It includes updated flight_cycles, flight_hours, cumulative_degradation, and updated_at. Reference files are never modified.

### manifest.json

Contains the batch ID, creation time, seed, row counts, ticks per flight, late threshold, and files included in the batch.

## Local setup

Python 3.10 or newer is required. The Docker image uses Python 3.11 because the code uses modern type annotations.

~~~bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
~~~

Run a small smoke test:

~~~bash
NUM_NEW_FLIGHTS=5 python main.py
~~~

Run the default batch:

~~~bash
python main.py
~~~

The default is 5,000 flights and 100 telemetry ticks per flight. A run prints its immutable output path under data/processed/batches/<batch_id>/.

Validate an existing batch:

~~~bash
python validate_data.py data/processed/batches/<batch_id>
~~~

Use the factory directly for a deterministic test:

~~~python
from generate_cmapss_sensor import generate_relational_mock_data
from validate_data import validate_batch

batch_dir = generate_relational_mock_data(
    num_new_flights=100,
    ticks_per_flight=100,
    seed=42,
)
validate_batch(batch_dir)
~~~

Passing seed=42 makes generated values reproducible. Omitting the seed uses system randomness, while the batch ID remains unique.

## Google Cloud Storage

The pipeline generates and validates locally first. It uploads only when UPLOAD_TO_GCS=1 is set.

~~~bash
export GCS_BUCKET_NAME="your-gcs-bucket"
export UPLOAD_TO_GCS=1
python main.py
~~~

Authentication uses Google Application Default Credentials or GOOGLE_APPLICATION_CREDENTIALS pointing to a service-account file outside source control.

~~~bash
export GOOGLE_APPLICATION_CREDENTIALS="/secure/path/service-account.json"
~~~

The complete batch is uploaded below gs://bucket/batches/<batch_id>/ with these files: manifest.json, flight_data.csv, engine_sensor_data.parquet, and engine_state_snapshot.csv.

Never put credentials, private keys, or connection strings in source files, notebooks, or commits.

## Docker

~~~bash
docker build -t jet-engine-pipeline .
docker run --rm -e NUM_NEW_FLIGHTS=5 jet-engine-pipeline
~~~

For GCS, provide configuration through a secret-managed environment and mount credentials read-only. Production deployments should prefer Workload Identity or runtime Application Default Credentials over JSON keys.

## Validation rules

validate_data.py fails when it finds:

- Null or duplicate primary keys
- Orphan foreign keys
- aircraft.engine_count disagreeing with the engine master
- A flight assigned to a non-ACTIVE aircraft
- The same person assigned as pilot and copilot
- Overlapping flights for one pilot
- Telemetry whose aircraft disagrees with its flight or engine
- Duplicate telemetry sequence numbers for one flight and engine
- A sensor event outside the flight time window
- An ingest timestamp before its event timestamp
- A quality_flag inconsistent with the ingest delay
- A flight without telemetry or telemetry for an unknown flight

## Design decisions

Every batch is immutable for auditability and reproducibility. The factory uses a UUID suffix in batch_id and raises FileExistsError rather than overwriting an existing directory.

This stage does not make predictions, but telemetry includes accumulated engine wear for future mathematical modeling. Wear, cycles, and hours are updated after each flight and saved in the engine snapshot.

Historical files have different IDs, timestamps, or schemas. They remain under data/legacy/ for reference, but the current ingestion path reads only data/reference/ and the generated batch directory.

## Known limitations and next steps

- There is no database engine enforcing PK/FK constraints yet; the file-based validator is the current contract.
- Sensor distributions are synthetic and should be calibrated against domain data.
- is_anomaly is a synthetic condition flag, not a ground-truth failure label.
- Maintenance work orders, failure modes, replacement events, and RUL labels are not present yet.
- There is no scheduler, retry policy, or GCS ingestion monitoring yet.
- No mathematical predictive model is implemented yet.
- A full automated test suite and CI pipeline are still future work.

Recommended next steps are schema and data-contract versioning, maintenance and failure event tables, domain review of distributions, and mathematical prediction equations on validated batches.

## Troubleshooting

### FileNotFoundError while reading reference data

Check that master files are under data/reference/ and that filenames match exactly, including the space before .csv in aircraft_data .csv.

### GCS_BUCKET_NAME is required

Set GCS_BUCKET_NAME only when using UPLOAD_TO_GCS=1. For local generation, leave the upload flag unset.

### GCS authentication fails

Check Application Default Credentials, bucket IAM permissions, and GOOGLE_APPLICATION_CREDENTIALS. Never solve this by placing a key in source code.

### Validation fails for an old batch

Pass the complete directory data/processed/batches/<batch_id> to the validator. Do not validate a legacy file or mix files from different batch IDs.

## Data and safety note

The repository contains mock/reference data for development and testing. It is not real flight-operation data and must not be used directly for aviation safety decisions.
