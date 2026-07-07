# src/ingest/bronze_ingestor.py
import sys
import os
import pandas as pd
from datetime import datetime

# ดึงระบบ Path จาก config.py นอกสุดเข้ามาใช้
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
import config

class BronzeIngestor:
    """พิมพ์เขียวเครื่องจักรสำหรับปั๊มข้อมูลดิบ (CSV) เข้าสู่ Bronze Layer (Parquet Format)"""
    
    def __init__(self):
        self.raw_path = config.RAW_DIR
        self.bronze_path = config.BRONZE_DIR
        # สร้างโฟลเดอร์ปลายทางอัตโนมัติถ้ายังไม่มี
        os.makedirs(self.bronze_path, exist_ok=True)

    def log(self, message: str):
        """ระบบพ่น Log ส่วนกลางของ Class"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [BRONZE_INGEST]: {message}")

    def ingest_file(self, csv_filename: str, output_parquet_name: str):
        """อ่านไฟล์ดิบ, หยอด Metadata, และบันทึกเป็น Parquet"""
        source_file = os.path.join(self.raw_path, csv_filename)
        target_file = os.path.join(self.bronze_path, f"{output_parquet_name}.parquet")
        
        # ตรวจสอบระบบเผื่อกรณีไฟล์หาย สคริปต์จะได้ไม่พังกลางคัน
        if not os.path.exists(source_file):
            self.log(f"⚠️ ไม่พบไฟล์: {csv_filename} (ข้ามขั้นตอน)")
            return

        try:
            self.log(f"กำลังปั๊มไฟล์ {csv_filename} ...")
            
            # 1. โหลดข้อมูลเข้า DataFrame
            df = pd.read_csv(source_file)
            
            # 2. ทำ Data Audit Columns (หยอด Metadata)
            df['ingest_time'] = pd.Timestamp.now()
            df['data_source_type'] = 'local_raw_csv'
            
            # 3. เซฟลงหลุม Bronze เป็น Parquet
            df.to_parquet(target_file, index=False)
            self.log(f"✅ สำเร็จ! ปั๊มออกเป็น -> {output_parquet_name}.parquet [จำนวน {len(df)} แถว]")
            
        except Exception as e:
            self.log(f"❌ บั๊กแดกที่ไฟล์ {csv_filename}: {str(e)}")

if __name__ == "__main__":
    # ปั๊ม Object ออกมาจากพิมพ์เขียว
    pipeline = BronzeIngestor()
    
    # แมปปิ้งชื่อไฟล์ดิบ กับชื่อตารางระบบหลังบ้าน (หัก Data Dict ออกตามที่คุยกัน)
    files_to_process = {
        "Aircraft Data Dictionary - aircraft_data (master).csv": "bronze_aircraft_master",
        "Aircraft Data Dictionary - aircraft_model_ref.csv": "bronze_aircraft_model_ref",
        "Aircraft Data Dictionary - airport_ref.csv": "bronze_airport_ref",
        "Aircraft Data Dictionary - engine_data.csv": "bronze_engine_master",
        "Aircraft Data Dictionary - engine_model_ref.csv": "bronze_engine_model_ref",
        "Aircraft Data Dictionary - engine_sensor_data.csv": "bronze_engine_sensor_data",
        "Aircraft Data Dictionary - flight_data.csv": "bronze_flight_data",
        "Aircraft Data Dictionary - pilot_data.csv": "bronze_pilot_data",
        "Aircraft Data Dictionary - pilot_rank_ref.csv": "bronze_pilot_rank_ref",
        "Aircraft Data Dictionary - weather_ref.csv": "bronze_weather_ref"
    }
    
    pipeline.log("▶ Ingest to Bronze Layer...")
    
    for csv_file, parquet_name in files_to_process.items():
        pipeline.ingest_file(csv_file, parquet_name)
        
    pipeline.log("End First Pipeline Bronze Ingestion Finish")