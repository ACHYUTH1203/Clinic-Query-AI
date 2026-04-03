import asyncio
import logging
from vanna.core.tool import ToolContext
from vanna.core.user.models import User
from vanna_setup import agent

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

qa_pairs = [
    # Patients
    ("How many patients do we have?", "SELECT COUNT(*) AS total_patients FROM patients;"),
    ("List all patients in Bengaluru", "SELECT * FROM patients WHERE city = 'Bengaluru';"),
    ("Show me all female patients", "SELECT first_name, last_name, email FROM patients WHERE gender = 'F';"),

    # Doctors
    ("How many appointments does each doctor have?", "SELECT d.name, COUNT(a.id) AS appointment_count FROM doctors d LEFT JOIN appointments a ON d.id = a.doctor_id GROUP BY d.name;"),
    ("Who is the busiest doctor?", "SELECT d.name, COUNT(a.id) AS appt_count FROM doctors d JOIN appointments a ON d.id = a.doctor_id GROUP BY d.name ORDER BY appt_count DESC LIMIT 1;"),

    # Appointments
    ("How many cancelled appointments are there?", "SELECT COUNT(*) FROM appointments WHERE status = 'Cancelled';"),
    ("Show appointments for this month", "SELECT * FROM appointments WHERE strftime('%Y-%m', appointment_date) = strftime('%Y-%m', 'now');"),
    ("Show appointments for Dr. Rahul", "SELECT a.* FROM appointments a JOIN doctors d ON a.doctor_id = d.id WHERE d.name LIKE '%Rahul%';"),

    # Financial
    ("Show revenue by doctor", "SELECT d.name, SUM(t.cost) AS total_revenue FROM doctors d JOIN appointments a ON d.id = a.doctor_id JOIN treatments t ON a.id = t.appointment_id GROUP BY d.name ORDER BY total_revenue DESC;"),
    ("Total revenue from all invoices", "SELECT SUM(total_amount) AS total_revenue FROM invoices;"),
    ("Show unpaid invoices", "SELECT * FROM invoices WHERE status != 'Paid';"),
    ("What is the average treatment cost?", "SELECT AVG(cost) FROM treatments;"),

    # Time-based
    ("Show appointments from the last 3 months", "SELECT * FROM appointments WHERE appointment_date >= date('now', '-3 months');"),
    ("Show monthly appointment count for the past 6 months", "SELECT strftime('%Y-%m', appointment_date) AS month, COUNT(*) FROM appointments WHERE appointment_date >= date('now', '-6 months') GROUP BY month ORDER BY month;"),
    ("Which city has the most patients?", "SELECT city, COUNT(*) AS patient_count FROM patients GROUP BY city ORDER BY patient_count DESC LIMIT 1;")
]

async def seed_database_knowledge():
    admin_user = User(id="admin", email="admin@example.com", group_memberships=["admin"])
    context = ToolContext(
        user=admin_user,
        conversation_id="training_session",
        request_id="seed_001",
        agent_memory=agent.agent_memory
    )

    schema_info = """
    --- CRITICAL SYSTEM INSTRUCTIONS ---
    1. STRICT SCHEMA ENFORCEMENT: You are a strict SQL assistant. You MUST ONLY use the exact tables and columns provided in the DATABASE SCHEMA below.
    2. NO HALLUCINATIONS: NEVER invent, guess, or assume table names. (e.g., absolutely NO 'sales', 'visits', 'departments', 'revenue_table').
    3. SQLITE DIALECT ONLY: You are querying a SQLite database. 
       - NEVER use DATE_TRUNC. Use strftime('%Y-%m', column_name) for months.
       - NEVER use DAYOFWEEK(). Use CAST(strftime('%w', column_name) AS INTEGER).

    --- DATABASE SCHEMA (DDL) ---
    CREATE TABLE patients (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, phone TEXT, date_of_birth DATE, gender TEXT, city TEXT, registered_date DATE);
    CREATE TABLE doctors (id INTEGER PRIMARY KEY, name TEXT, specialization TEXT, department TEXT, phone TEXT);
    CREATE TABLE appointments (id INTEGER PRIMARY KEY, patient_id INTEGER, doctor_id INTEGER, appointment_date DATETIME, status TEXT, notes TEXT, FOREIGN KEY(patient_id) REFERENCES patients(id), FOREIGN KEY(doctor_id) REFERENCES doctors(id));
    CREATE TABLE treatments (id INTEGER PRIMARY KEY, appointment_id INTEGER, treatment_name TEXT, cost REAL, duration_minutes INTEGER, FOREIGN KEY(appointment_id) REFERENCES appointments(id));
    CREATE TABLE invoices (id INTEGER PRIMARY KEY, patient_id INTEGER, invoice_date DATE, total_amount REAL, paid_amount REAL, status TEXT, FOREIGN KEY(patient_id) REFERENCES patients(id));

    --- DATABASE LOGIC & RULES ---
    - DOCTOR REVENUE / DEPARTMENT REVENUE: You MUST Join 'doctors' -> 'appointments' -> 'treatments' and SUM 'treatments.cost'.
    - TOTAL REVENUE: SUM 'invoices.total_amount' from the invoices table.
    - PATIENT VISITS: Count the rows in the 'appointments' table grouped by patient_id.
    - APPOINTMENT DURATION: Use 'duration_minutes' from the 'treatments' table.
    - OVERDUE INVOICES: Check WHERE status = 'Overdue' in the 'invoices' table.
    """

    
    await agent.agent_memory.save_text_memory(content=schema_info, context=context)

    for question, sql in qa_pairs:
        await agent.agent_memory.save_tool_usage(
            question=question, tool_name="run_sql", args={"sql": sql}, context=context, success=True
        )
    logging.info("Gold-Standard pairs seeded.")

if __name__ == "__main__":
    asyncio.run(seed_database_knowledge())