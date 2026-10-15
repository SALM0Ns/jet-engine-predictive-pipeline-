"""Upload a complete generated batch to Google Cloud Storage."""

from __future__ import annotations

import os
from pathlib import Path

from google.cloud import storage


REQUIRED_FILES = ("manifest.json", "flight_data.csv", "engine_sensor_data.parquet", "engine_state_snapshot.csv")


def upload_batch_to_gcs(batch_dir: str | Path, bucket_name: str | None = None) -> None:
    """Upload one immutable batch to ``gs://<bucket>/batches/<batch_id>/``.

    Authentication is deliberately delegated to Application Default Credentials or
    ``GOOGLE_APPLICATION_CREDENTIALS``; no key is stored in source code.
    """
    batch_dir = Path(batch_dir).resolve()
    bucket_name = bucket_name or os.getenv("GCS_BUCKET_NAME")
    if not bucket_name:
        raise RuntimeError("GCS_BUCKET_NAME is required when UPLOAD_TO_GCS=1")
    missing = [name for name in REQUIRED_FILES if not (batch_dir / name).is_file()]
    if missing:
        raise FileNotFoundError(f"Batch is incomplete: {missing}")
    bucket = storage.Client().bucket(bucket_name)
    prefix = f"batches/{batch_dir.name}"
    for filename in REQUIRED_FILES:
        blob = bucket.blob(f"{prefix}/{filename}")
        blob.upload_from_filename(batch_dir / filename)
        print(f"Uploaded gs://{bucket_name}/{prefix}/{filename}")

