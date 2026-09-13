# Data layout

`data/reference/` contains the small, curated master tables used by the factory:
aircraft, engines, pilots, airports, and weather. These are inputs and are never
mutated by a generation run.

`data/processed/batches/<batch_id>/` is the only canonical output location. A
batch is immutable and includes a manifest, flight fact table, telemetry fact
table, and engine-state snapshot. Load the files from the same batch ID together.

`data/legacy/` contains historical sample files retained for reference only.
They must not be included in the production ingestion path or joined with a
generated batch.

`data/Raw/` is reserved for unprocessed external source drops.

## Google Cloud Storage

Set `UPLOAD_TO_GCS=1` and `GCS_BUCKET_NAME=<bucket>` to upload a complete batch
to `gs://<bucket>/batches/<batch_id>/`. Authentication uses Application Default
Credentials or `GOOGLE_APPLICATION_CREDENTIALS`; credentials are never read from
source files.
