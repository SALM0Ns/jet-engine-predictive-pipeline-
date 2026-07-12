import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta, timezone
import os
import time # เอามาจับเวลาเล่นๆ ว่า 1 ล้านแถวใช้เวลาเท่าไหร่

def generate_relational_mock_data(num_new_flights=5000): # ตั้งต้นที่ 5,000 ไฟลต์
    start_timer = time.time()
    
    BASE_PATH = r"D:\Work\Coding\Python\Data Engineer\Aircradt Data\data\Raw"
    
    print("📖 Loading the 7 Reference Master Data tables...")
    try:
        df_aircraft = pd.read_csv(f"{BASE_PATH}/Aircraft Data Dictionary - aircraft_data .csv")
        df_engine = pd.read_csv(f"{BASE_PATH}/Aircraft Data Dictionary - engine_data.csv")
        df_pilot = pd.read_csv(f"{BASE_PATH}/Aircraft Data Dictionary - pilot_data.csv")
        df_airport = pd.read_csv(f"{BASE_PATH}/Aircraft Data Dictionary - airport_data.csv")
        df_weather = pd.read_csv(f"{BASE_PATH}/Aircraft Data Dictionary - weather_data.csv")
    except Exception as e:
        print(f"❌ Failed to load reference data. Please check your path: {e}")
        return

    for df in [df_aircraft, df_engine, df_pilot, df_airport, df_weather]:
        df.columns = df.columns.str.strip()

    print(f"🚀 Initiating generation of {num_new_flights} new flight records...")
    
    new_flights = []
    start_date = datetime(2026, 7, 10, 8, 0, 0, tzinfo=timezone.utc) 
    
    aircraft_ids = df_aircraft['aircraft_id'].tolist()
    pilot_ids = df_pilot['pilot_id'].tolist()
    airports = df_airport['airport_code'].tolist()
    weathers = df_weather['weather_name'].tolist() 
    
    for i in range(1, num_new_flights + 1):
        flight_id = f"FLT_20260710_{i:04d}"
        flight_no = f"MIL{random.randint(10,99)}{i:03d}"
        
        ac_id = random.choice(aircraft_ids)
        plt_id = random.choice(pilot_ids)
        coplt_id = random.choice([p for p in pilot_ids if p != plt_id]) 
        
        dep_ap = random.choice(airports)
        arr_ap = random.choice([a for a in airports if a != dep_ap])
        
        duration_hours = random.uniform(1.0, 3.0)
        dep_time = start_date + timedelta(hours=random.uniform(1, 4) * i)
        arr_time = dep_time + timedelta(hours=duration_hours)
        weather = random.choice(weathers)
        
        current_time_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        new_flights.append({
            "flight_id": flight_id,
            "flight_no": flight_no,
            "aircraft_id": ac_id,
            "pilot_id": plt_id,
            "copilot_id": coplt_id,
            "departure_airport": dep_ap,
            "arrival_airport": arr_ap,
            "scheduled_departure": dep_time.isoformat().replace("+00:00", "Z"),
            "actual_departure": (dep_time + timedelta(minutes=random.randint(0,10))).isoformat().replace("+00:00", "Z"),
            "scheduled_arrival": arr_time.isoformat().replace("+00:00", "Z"),
            "actual_arrival": (arr_time + timedelta(minutes=random.randint(0,10))).isoformat().replace("+00:00", "Z"),
            "flight_status": "COMPLETED",
            "weather_condition": weather,
            "created_at": current_time_str,
            "updated_at": current_time_str
        })
        
    df_new_flights = pd.DataFrame(new_flights)
    
    print("📈 Simulating 1 MILLION time-series sensor data points... (This might take a minute ⏳)")
    
    sensor_rows = []
    event_counter = 1
    
    for _, flight in df_new_flights.iterrows():
        flt_id = flight['flight_id']
        ac_id = flight['aircraft_id']
        
        active_engines = df_engine[df_engine['aircraft_id'].str.strip() == ac_id.strip()]
        ac_spec = df_aircraft[df_aircraft['aircraft_id'].str.strip() == ac_id.strip()].iloc[0]
        max_altitude = int(ac_spec.get('cruise_altitude_ft', 35000))
        max_speed = float(ac_spec.get('max_speed_knots', 1500))
        
        num_ticks = 100 # 🔥 ปรับเป็น 100 Ticks เพื่อให้ได้ดาต้า 1 ล้านแถว!
        
        for tick in range(1, num_ticks + 1):
            if tick < 15: 
                current_alt = (max_altitude / 15) * tick
                current_speed = (max_speed / 2) + (tick * 20)
            elif tick > 85: 
                current_alt = max_altitude - ((max_altitude / 15) * (tick - 85))
                current_speed = (max_speed / 2) - ((tick - 85) * 20)
            else: 
                current_alt = max_altitude + random.randint(-500, 500)
                current_speed = (max_speed * 0.8) + random.randint(-20, 20)

            for _, eng in active_engines.iterrows():
                eng_id = eng['engine_id']
                
                max_rpm_spec = int(eng.get('max_rpm', 12000))
                max_temp_spec = float(eng.get('max_temp_c', 950))
                
                degradation = (tick / num_ticks) * 25
                weather_impact = 30 if flight['weather_condition'] == 'Thunderstorm' else 0
                
                temp = (max_temp_spec * 0.65) + degradation + weather_impact + random.uniform(-5, 5)
                rpm = (max_rpm_spec * 0.78) - (degradation * 2) + random.randint(-50, 50)
                
                is_anomaly = temp > (max_temp_spec * 0.72)
                status = "WARNING" if is_anomaly else "OK"
                event_id = f"EVT_MOCK_{event_counter:08d}"
                
                sensor_time = datetime.fromisoformat(flight['actual_departure'].replace('Z', '+00:00')) + timedelta(minutes=tick)
                ingest_time_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                
                sensor_rows.append({
                    "event_id": event_id,
                    "flight_id": flt_id,
                    "aircraft_id": ac_id,
                    "engine_id": eng_id,
                    "event_time": sensor_time.isoformat().replace("+00:00", "Z"),
                    "ingest_time": ingest_time_str,
                    "sequence_no": tick,
                    "altitude_ft": int(current_alt),
                    "speed_knots": round(current_speed, 1),
                    "engine_temp_c": round(temp, 1),
                    "engine_pressure_kpa": round(200 + (rpm * 0.005) + random.uniform(-2,2), 1),
                    "fuel_flow_kg_h": round(1500 + (current_speed * 1.2) + random.uniform(-10,10), 1),
                    "vibration_hz": round(10 + (tick * 0.05) + random.uniform(-0.5, 0.5), 1),
                    "rpm": int(rpm),
                    "oil_temp_c": round((temp * 0.15) + random.uniform(-2,2), 1),
                    "oil_pressure_kpa": round(350 - (tick * 0.2) + random.randint(-5, 5), 1),
                    "status": status,
                    "quality_flag": "GOOD",
                    "is_anomaly": is_anomaly,
                    "source": "automated_1M_stress_test"
                })
                event_counter += 1

    df_new_sensors = pd.DataFrame(sensor_rows)

    print("🔄 Updating engine accumulating metrics in Memory...")
    for _, flight in df_new_flights.iterrows():
        ac_id = flight['aircraft_id']
        dep = datetime.fromisoformat(flight['actual_departure'].replace('Z', '+00:00'))
        arr = datetime.fromisoformat(flight['actual_arrival'].replace('Z', '+00:00'))
        flight_duration_hours = (arr - dep).total_seconds() / 3600
        
        update_time_str = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        
        engine_mask = df_engine['aircraft_id'].str.strip() == ac_id.strip()
        df_engine.loc[engine_mask, 'flight_cycles'] += 1
        df_engine.loc[engine_mask, 'flight_hours'] += round(flight_duration_hours, 1)
        df_engine.loc[engine_mask, 'updated_at'] = update_time_str

        pilot_mask = df_pilot['pilot_id'].str.strip() == flight['pilot_id'].strip()
        df_pilot.loc[pilot_mask, 'total_flight_hours'] += round(flight_duration_hours, 1)
        df_pilot.loc[pilot_mask, 'updated_at'] = update_time_str

    # 💾 5. Export Data (ส่งเข้าโฟลเดอร์ Raw ล้วนๆ ไม่แตะของเดิมหน้าบ้าน)
    OUTPUT_DIR = f"{BASE_PATH}/data/Raw"
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("💾 Saving files to disk... (Parquet compression in progress)")
    df_new_flights.to_csv(f"{OUTPUT_DIR}/expanded_flight_data.csv", index=False)
    df_new_sensors.to_parquet(f"{OUTPUT_DIR}/expanded_engine_sensor_data.parquet", index=False)
    
    # เซฟไฟล์ Master Data ตัวใหม่แยกออกมาไว้สำหรับทำ Ingest ทับของเดิม
    df_engine.to_csv(f"{OUTPUT_DIR}/updated_engine_data.csv", index=False)
    df_pilot.to_csv(f"{OUTPUT_DIR}/updated_pilot_data.csv", index=False)
    
    end_timer = time.time()
    
    print("\n✨ 1 MILLION ROWS GENERATION COMPLETED! ✨")
    print(f"⏱️ Time taken: {round(end_timer - start_timer, 2)} seconds")
    print(f"📁 Flight data exported: {len(df_new_flights):,} rows")
    print(f"📁 Sensor data exported: {len(df_new_sensors):,} rows")
    print(f"📁 Updated Master Data ready for Ingest: updated_engine_data.csv, updated_pilot_data.csv")

if __name__ == "__main__":
    generate_relational_mock_data()