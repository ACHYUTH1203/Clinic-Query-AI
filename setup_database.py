import sqlite3
import random
import logging
from datetime import datetime, timedelta
from typing import List, Tuple, Optional

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

DB_NAME = 'clinic.db'
NUM_DOCTORS = 15
NUM_PATIENTS = 200
NUM_APPOINTMENTS = 500
NUM_TREATMENTS = 350
NUM_INVOICES = 300

def create_schema(cursor: sqlite3.Cursor) -> None:
    logging.info("Creating database schema...")
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS patients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            city TEXT,
            registered_date DATE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS doctors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            specialization TEXT,
            department TEXT,
            phone TEXT
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS appointments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            doctor_id INTEGER,
            appointment_date DATETIME,
            status TEXT,
            notes TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id),
            FOREIGN KEY(doctor_id) REFERENCES doctors(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS treatments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            appointment_id INTEGER,
            treatment_name TEXT,
            cost REAL,
            duration_minutes INTEGER,
            FOREIGN KEY(appointment_id) REFERENCES appointments(id)
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patient_id INTEGER,
            invoice_date DATE,
            total_amount REAL,
            paid_amount REAL,
            status TEXT,
            FOREIGN KEY(patient_id) REFERENCES patients(id)
        )
    """)

def get_random_date(days_back: int, time_too: bool = False) -> str:
    """Generates realistic dates/times within a timeframe."""
    random_days = random.randint(0, days_back)
    dt = datetime.now() - timedelta(days=random_days)
    if time_too:
        dt = dt.replace(hour=random.randint(9, 18), minute=random.choice([0, 15, 30, 45]), second=0)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return dt.strftime('%Y-%m-%d')

def insert_doctors(cursor: sqlite3.Cursor) -> None:
    """Inserts 15 doctors with Indian names and 10-digit mobile numbers."""
    specializations = [
        ("Dermatology", "Skin Care"),
        ("Cardiology", "Heart Center"),
        ("Orthopedics", "Bone & Joint"),
        ("General", "Primary Care"),
        ("Pediatrics", "Childrens Unit")
    ]
    
    first_names = ["Rahul", "Amit", "Vikram", "Siddharth", "Arjun", "Priya", "Neha", "Anjali", "Sneha", "Divya"]
    last_names = ["Sharma", "Patel", "Singh", "Reddy", "Rao", "Desai", "Joshi", "Iyer", "Menon", "Nair"]
    
    data = []
    for _ in range(NUM_DOCTORS):
        name = f"Dr. {random.choice(first_names)} {random.choice(last_names)}"
        spec, dept = random.choice(specializations)
        phone = f"+91-9{random.randint(100000000, 999999999)}"
        data.append((name, spec, dept, phone))
        
    cursor.executemany("INSERT INTO doctors (name, specialization, department, phone) VALUES (?, ?, ?, ?)", data)

def insert_patients(cursor: sqlite3.Cursor) -> None:
    """Inserts 200 patients strictly spread across 10 cities with some NULL emails/phones."""
    
    cities = [
        "Bengaluru", "Mumbai", "Delhi", "Hyderabad", "Chennai", 
        "Pune", "Ahmedabad", "Jaipur", "Kolkata", "Surat"
    ]

    first_names = [
        "Achyuth", "Rohan", "Karthik", "Aditya", "Karan", "Vivek", "Meera", "Pooja", "Ritu", "Ananya", "Kavya", "Shruti",
        "Rahul", "Amit", "Vikram", "Siddharth", "Arjun", "Manish", "Sanjay", "Anil", "Sunil", "Rajesh", "Priya", "Neha",
        "Anjali", "Sneha", "Divya", "Aishwarya", "Swati", "Kiran", "Rekha", "Rashmi", "Jyoti", "Nisha", "Rishabh", "Pranav",
        "Ishaan", "Dhruv", "Riya", "Aarohi", "Sanya", "Tanvi", "Nandini", "Yash", "Kabir", "Aryan", "Isha", "Tara", "Roshni"
    ]

    last_names = [
        "Rayal", "Kumar", "Gupta", "Bose", "Chauhan", "Verma", "Pandey", "Yadav", "Das", "Mukherjee", "Sharma", "Patel",
        "Singh", "Reddy", "Rao", "Desai", "Joshi", "Iyer", "Menon", "Nair", "Agarwal", "Jain", "Khatri", "Bhatia", "Ahuja",
        "Kapoor", "Malhotra", "Chopra", "Mehra", "Kulkarni", "Patil", "Deshmukh", "Banerjee", "Chatterjee", "Mishra", 
        "Tiwari", "Shukla", "Srivastava", "Bhardwaj", "Rajput", "Sen", "Nath", "Pillai", "Gowda", "Hegde", "Bhatt", "Dalal"
    ]
    data = []
    for _ in range(NUM_PATIENTS):
        fname = random.choice(first_names)
        lname = random.choice(last_names)
        
        email = f"{fname.lower()}.{lname.lower()}{random.randint(1,999)}@gmail.com" if random.random() > 0.15 else None
        phone = f"+91-9{random.randint(100000000, 999999999)}" if random.random() > 0.15 else None
        
        dob = get_random_date(days_back=25000)
        gender = random.choice(["M", "F"]) 
        city = random.choice(cities)
        reg_date = get_random_date(days_back=365)
        
        data.append((fname, lname, email, phone, dob, gender, city, reg_date))
        
    cursor.executemany("""
        INSERT INTO patients (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, data)

def insert_appointments(cursor: sqlite3.Cursor) -> None:
    """Inserts 500 appointments mapping patients to doctors."""
    patient_ids = list(range(1, NUM_PATIENTS + 1))
    patient_weights = [random.randint(1, 10) for _ in patient_ids]
    
    doctor_ids = list(range(1, NUM_DOCTORS + 1))
    doctor_weights = [random.randint(1, 5) for _ in doctor_ids]

    statuses = ["Scheduled", "Completed", "Cancelled", "No-Show"]
    status_weights = [15, 65, 10, 10]
    
    data = []
    for _ in range(NUM_APPOINTMENTS):
        p_id = random.choices(patient_ids, weights=patient_weights, k=1)[0]
        d_id = random.choices(doctor_ids, weights=doctor_weights, k=1)[0]
        appt_date = get_random_date(days_back=365, time_too=True)
        status = random.choices(statuses, weights=status_weights, k=1)[0]
        notes = random.choice(["Routine checkup", "Follow-up", "Patient reported pain", "Prescription renewal", "General consultation", None, None, None])
        
        data.append((p_id, d_id, appt_date, status, notes))
        
    cursor.executemany("""
        INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes)
        VALUES (?, ?, ?, ?, ?)
    """, data)

def insert_treatments(cursor: sqlite3.Cursor) -> None:
    """Inserts 350 treatments explicitly linked to completed appointments."""
    cursor.execute("SELECT id FROM appointments WHERE status = 'Completed'")
    completed_appts = [row[0] for row in cursor.fetchall()]
    
    target_treatments = min(NUM_TREATMENTS, len(completed_appts))
    treatment_names = ["Consultation", "Blood Test", "X-Ray", "Physiotherapy", "Vaccination", "ECG", "MRI Scan", "Ultrasound", "Dressing Change"]
    
    selected_appts = random.choices(completed_appts, k=target_treatments)
    
    data = []
    for appt_id in selected_appts:
        name = random.choice(treatment_names)
        cost = round(random.uniform(50.0, 5000.0), 2)
        duration = random.choice([15, 30, 45, 60, 90, 120])
        data.append((appt_id, name, cost, duration))
        
    cursor.executemany("""
        INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes)
        VALUES (?, ?, ?, ?)
    """, data)

def insert_invoices(cursor: sqlite3.Cursor) -> None:
    """Inserts 300 invoices ensuring logical paid amounts based on status."""
    statuses = ["Paid", "Pending", "Overdue"]
    
    data = []
    for _ in range(NUM_INVOICES):
        p_id = random.randint(1, NUM_PATIENTS)
        inv_date = get_random_date(days_back=365)
        total_amount = round(random.uniform(50.0, 5000.0), 2)
        status = random.choice(statuses)
        
        if status == "Paid":
            paid_amount = total_amount
        elif status == "Overdue":
            paid_amount = 0.0
        else: 
            paid_amount = round(total_amount * random.uniform(0.0, 0.7), 2)
            
        data.append((p_id, inv_date, total_amount, paid_amount, status))
        
    cursor.executemany("""
        INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status)
        VALUES (?, ?, ?, ?, ?)
    """, data)

def main() -> None:
    conn = None
    try:
        logging.info(f"Connecting to database: {DB_NAME}")
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        
        cursor.execute("PRAGMA foreign_keys = ON;")
        
        create_schema(cursor)
        insert_doctors(cursor)
        insert_patients(cursor)
        insert_appointments(cursor)
        insert_treatments(cursor)
        insert_invoices(cursor)
        
        conn.commit()
        logging.info("Transaction committed successfully.")
        
        print(f"Created {NUM_PATIENTS} patients, {NUM_DOCTORS} doctors, {NUM_APPOINTMENTS} appointments, {NUM_TREATMENTS} treatments, and {NUM_INVOICES} invoices.")
        
    except sqlite3.Error as e:
        logging.error(f"Database error occurred: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()