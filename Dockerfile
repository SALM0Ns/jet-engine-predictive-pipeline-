FROM python:3.9-slim
WORKDIR /app

# 1. ก๊อปปี้ไฟล์ requirements เข้ามาก่อน
COPY requirements.txt .

# 2. ติดตั้ง Library ตามที่ระบุไว้
RUN pip install --no-cache-dir -r requirements.txt

# 3. 🌟 บรรทัดนี้สำคัญ: ก๊อปปี้ "ทุกไฟล์" (รวมถึง main.py, generate_*.py ฯลฯ) เข้าไปในกล่อง
COPY . .

# 4. สั่งรันผู้จัดการคิวงานของเรา
CMD ["python", "-u", "main.py"]