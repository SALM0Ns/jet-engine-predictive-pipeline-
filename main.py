import generate_cmapss_sensor
import upload_to_azure

def run_automated_pipeline():
    print("===  Starting Automated Aircraft Data Pipeline ===")
    
    # 1. สั่งปั๊มข้อมูล (กำหนด Path ให้ตรงกับโครงสร้างใน Docker)
    ENGINE_DATA_PATH = '/app/data/refer/Aircraft Data Dictionary - engine_data.csv' 
    OUTPUT_DIR = '/app/data/Raw'
    
    print(">> Phase 1: Generating Simulated Sensor Data...")
    # ลองปั๊มสัก 100 รอบต่อเครื่องก่อน จะได้รันทดสอบไวๆ
    generate_cmapss_sensor.generate_realistic_sensor_data(ENGINE_DATA_PATH, OUTPUT_DIR, rows_per_engine=100)
    
    print("\n>> Phase 2: Uploading Data to Azure Data Lake...")
    # 2. สั่งอัปโหลด
    upload_to_azure.upload_file_to_cloud()
    
    print("\n===  Pipeline Completed Successfully! ===")

if __name__ == "__main__":
    run_automated_pipeline()