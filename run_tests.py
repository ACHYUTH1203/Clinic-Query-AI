import asyncio
import logging
import pandas as pd
from vanna_setup import agent
from seed_memory import seed_database_knowledge
from vanna.core.user import User, RequestContext

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

TEST_QUESTIONS = [
    "How many patients do we have?",
    "List all doctors and their specializations",
    "Show me appointments for last month",
    "Which doctor has the most appointments?",
    "What is the total revenue?",
    "Show revenue by doctor",
    "How many cancelled appointments last quarter?",
    "Top 5 patients by spending",
    "Average treatment cost by specialization",
    "Show monthly appointment count for the past 6 months",
    "Which city has the most patients?",
    "List patients who visited more than 3 times",
    "Show unpaid invoices",
    "What percentage of appointments are no-shows?",
    "Show the busiest day of the week for appointments",
    "Revenue trend by month",
    "Average appointment duration by doctor",
    "List patients with overdue invoices",
    "Compare revenue between departments",
    "Show patient registration trend by month"
]


SCHEMA_CONTEXT = """
[CRITICAL SCHEMA CONTEXT]
Tables available:
- patients (id, first_name, last_name, email, phone, date_of_birth, gender, city, registered_date)
- doctors (id, name, specialization, department, phone)
- appointments (id, patient_id, doctor_id, appointment_date, status, notes)
- treatments (id, appointment_id, treatment_name, cost, duration_minutes)
- invoices (id, patient_id, invoice_date, total_amount, paid_amount, status)

Rules: 
- For Revenue/Spending use SUM(treatments.cost) or SUM(invoices.total_amount). 
- NEVER use tables named 'sales', 'orders', 'departments', 'visits', etc.
- NEVER use DAYNAME() or DAYOFWEEK(). Use CAST(strftime('%w', column_name) AS INTEGER) for day of the week.
"""

async def run_automated_tests():
    logging.info("Auto-seeding memory for this session...")
    await seed_database_knowledge()

    logging.info("Starting automated NL2SQL tests...")
    
    passed_count = 0
    total_questions = len(TEST_QUESTIONS)
    results_content = "# NL2SQL Automated Test Results\n\n"
    
    test_user = User(id="test_user", email="test@example.com", group_memberships=['admin', 'user'])
    context = RequestContext(user=test_user, conversation_id="test_run")

    for i, question in enumerate(TEST_QUESTIONS, 1):
        logging.info(f"Testing Q{i}/{total_questions}: {question}")
        results_content += f"### Question {i}: {question}\n\n"
        
        try:
            final_text = ""
            generated_sql = ""
            data_preview = ""
            
            test_prompt = f"{question}\n\n{SCHEMA_CONTEXT}"

            async for chunk in agent.send_message(message=test_prompt, request_context=context):
                if hasattr(chunk, 'simple_component') and chunk.simple_component:
                    final_text += getattr(chunk.simple_component, 'text', '') + "\n"
                
                if hasattr(chunk, 'rich_component') and chunk.rich_component:
                    comp = chunk.rich_component
                    comp_type = str(getattr(comp, 'type', '')).lower()
                    
                    if 'code' in comp_type and getattr(comp, 'language', '').lower() == 'sql':
                        generated_sql = getattr(comp, 'code', '')
                        final_text += f"\n[Extracted SQL]\n{generated_sql}\n"
                        
                    elif 'table' in comp_type or 'data_grid' in comp_type:
                        data = getattr(comp, 'data', [])
                        if data:
                            df = pd.DataFrame(data)
                            data_preview = df.head(5).to_markdown()

            is_success = (
                "Tool completed successfully" in final_text
                and "Error executing query" not in final_text
                and "Tool failed" not in final_text
            )

            if is_success:
                results_content += "**Status:**  Passed\n\n"
                passed_count += 1
            else:
                results_content += "**Status:**  Failed\n\n"
                
            if generated_sql:
                results_content += f"**Generated SQL:**\n```sql\n{generated_sql}\n```\n\n"
            
            if data_preview:
                results_content += f"**Data Results (Top 5):**\n{data_preview}\n\n"
            
            results_content += f"**Agent Execution Log:**\n```text\n{final_text.strip()}\n```\n\n"

        except Exception as e:
            results_content += f"**Status:** Failed\n**Error:** {str(e)}\n\n"

        results_content += "---\n\n"
        await asyncio.sleep(1)

    results_content += f"## Final Score\n**{passed_count} out of {total_questions} questions passed.**\n"
    
    with open("RESULTS.md", "w", encoding="utf-8") as file:
        file.write(results_content)

    logging.info("Testing complete! Check RESULTS.md")

if __name__ == "__main__":
    asyncio.run(run_automated_tests())