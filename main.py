import os

import generate_cmapss_sensor
from upload_to_gcs import upload_batch_to_gcs
from validate_data import validate_batch

def run_automated_pipeline():
    print("===  Starting Automated Aircraft Data Pipeline ===")
    
    print(">> Phase 1: Generating Simulated Sensor Data...")
    flight_count = int(os.getenv("NUM_NEW_FLIGHTS", "5000"))
    batch_dir = generate_cmapss_sensor.generate_relational_mock_data(num_new_flights=flight_count)
    validate_batch(batch_dir)
    print(f">> Generated validated batch: {batch_dir}")

    if os.getenv("UPLOAD_TO_GCS") == "1":
        print("\n>> Phase 2: Uploading batch to Google Cloud Storage...")
        upload_batch_to_gcs(batch_dir)
    else:
        print("\n>> Phase 2 skipped (set UPLOAD_TO_GCS=1 to enable upload).")
    
    print("\n===  Pipeline Completed Successfully! ===")

if __name__ == "__main__":
    run_automated_pipeline()
