# config.py
import os

# 1. ค้นหา Path ปัจจุบันของโฟลเดอร์โปรเจกต์
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# 2. มาร์กจุดโฟลเดอร์เก็บ Data
DATA_DIR = os.path.join(BASE_DIR, "data")

# 3. กำหนดเส้นทางให้แต่ละ Layer
RAW_DIR = os.path.join(DATA_DIR, "01_raw")
BRONZE_DIR = os.path.join(DATA_DIR, "02_bronze")
SILVER_DIR = os.path.join(DATA_DIR, "03_silver")