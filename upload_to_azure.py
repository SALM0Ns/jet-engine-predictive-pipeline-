from azure.storage.blob import BlobServiceClient
from azure.core.exceptions import ResourceExistsError
import os

def upload_file_to_cloud():
    # 1. ใส่ Connection String ของคุณให้ถูกต้อง
    CONN_STR = "*****"
    CONTAINER_NAME = "enginedata" 
    
    print(f"🔍 DEBUG: กำลังจะส่งไปที่ห้องชื่อ -> '{CONTAINER_NAME}'")
    FILE_PATH = "/app/data/Raw/simulated_engine_sensor_data.parquet"
    FILE_NAME = os.path.basename(FILE_PATH)

    try:
        # เชื่อมต่อกับโกดังใหญ่
        blob_service_client = BlobServiceClient.from_connection_string(CONN_STR)
        
        # 🌟 สั่งให้ระบบเช็กและสร้างห้องให้อัตโนมัติ!
        try:
            blob_service_client.create_container(CONTAINER_NAME)
            print(f"🛠️ ระบบตรวจพบว่าไม่มีห้อง '{CONTAINER_NAME}' -> ทำการสร้างห้องให้ใหม่บน Azure สำเร็จ!")
        except ResourceExistsError:
            print(f"✅ เจอห้อง '{CONTAINER_NAME}' ในระบบแล้ว พร้อมลุย!")

        # เตรียมโยนไฟล์ลงห้อง
        blob_client = blob_service_client.get_blob_client(
            container=CONTAINER_NAME, 
            blob=FILE_NAME
        )
        
        print(f"🚀 กำลังอัปโหลดไฟล์ {FILE_NAME} ขึ้น Cloud...")
        with open(FILE_PATH, "rb") as data:
            blob_client.upload_blob(data, overwrite=True)
            
        print("🎉 อัปโหลดสำเร็จ! ข้อมูลระดับ NASA ของคุณไปนอนรออยู่บน Cloud แล้ว!")
        
    except Exception as e:
        print(f"❌ เกิดข้อผิดพลาด: {e}")

if __name__ == "__main__":
    upload_file_to_cloud()