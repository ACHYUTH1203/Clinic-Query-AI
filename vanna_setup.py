import os
import re 
import logging
import requests
from dotenv import load_dotenv

from vanna import Agent, DefaultWorkflowHandler
from vanna.core.registry import ToolRegistry
from vanna.core.user import UserResolver, User, RequestContext
from vanna.tools import RunSqlTool, VisualizeDataTool
from vanna.tools.agent_memory import SaveQuestionToolArgsTool, SearchSavedCorrectToolUsesTool
from vanna.integrations.sqlite import SqliteRunner
from vanna.integrations.local.agent_memory import DemoAgentMemory
from vanna.components import RichTextComponent, ButtonGroupComponent

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
load_dotenv()


class ValidatedSqliteRunner(SqliteRunner):
    def run_sql(self, sql, *args, **kwargs):
        if hasattr(sql, 'sql'):
            actual_sql = sql.sql
        elif isinstance(sql, dict) and 'sql' in sql:
            actual_sql = sql['sql']
        else:
            actual_sql = str(sql)
            
        upper_sql = actual_sql.upper().strip()
        
        if not upper_sql.startswith("SELECT") and not upper_sql.startswith("PRAGMA"):
            raise ValueError("Security Error: Only SELECT queries are allowed.")
        
        forbidden = [
            "DROP", "DELETE", "UPDATE", "INSERT", "ALTER", 
            "EXEC", "GRANT", "REVOKE", "SHUTDOWN", "XP_", "SP_", "SQLITE_MASTER"
        ]
        

        for word in forbidden:
            if re.search(r'\b' + word + r'\b', upper_sql):
                raise ValueError(f"Security Error: Dangerous keyword '{word}' detected.")
                
        return super().run_sql(sql, *args, **kwargs)


class ClinicDashboardHandler(DefaultWorkflowHandler):
    def __init__(self):
        super().__init__(welcome_message="# 🏥 ClinicQueryAI Dashboard\nWelcome. I am your medical data assistant. How can I help you today?")

    async def get_system_prompt(self, agent, user, conversation) -> str:
        
        base_prompt = await super().get_system_prompt(agent, user, conversation)
        schema_instructions = """
        --- CRITICAL DATABASE SCHEMA ---
        You are querying a SQLite database. You MUST ONLY use the exact tables and columns provided below. 
        NEVER guess or invent tables (e.g., do NOT use 'sales', 'orders', 'patient_spending', etc.).
        
        CREATE TABLE patients (id INTEGER PRIMARY KEY, first_name TEXT, last_name TEXT, email TEXT, phone TEXT, date_of_birth DATE, gender TEXT, city TEXT, registered_date DATE);
        CREATE TABLE doctors (id INTEGER PRIMARY KEY, name TEXT, specialization TEXT, department TEXT, phone TEXT);
        CREATE TABLE appointments (id INTEGER PRIMARY KEY, patient_id INTEGER, doctor_id INTEGER, appointment_date DATETIME, status TEXT, notes TEXT, FOREIGN KEY(patient_id) REFERENCES patients(id), FOREIGN KEY(doctor_id) REFERENCES doctors(id));
        CREATE TABLE treatments (id INTEGER PRIMARY KEY, appointment_id INTEGER, treatment_name TEXT, cost REAL, duration_minutes INTEGER, FOREIGN KEY(appointment_id) REFERENCES appointments(id));
        CREATE TABLE invoices (id INTEGER PRIMARY KEY, patient_id INTEGER, invoice_date DATE, total_amount REAL, paid_amount REAL, status TEXT, FOREIGN KEY(patient_id) REFERENCES patients(id));
        
        RULES:
        - For Revenue: SUM(treatments.cost) for doctors/departments, or SUM(invoices.total_amount) for overall.
        - SQLite Dialect: Do NOT use DATE_TRUNC or DAYOFWEEK().
        - NEVER use DAYNAME() or DAYOFWEEK(). Use CAST(strftime('%w', column_name) AS INTEGER) for day of the week.
        """
        
        return base_prompt + "\n\n" + schema_instructions

    async def get_starter_ui(self, agent, user, conversation):
        components = await super().get_starter_ui(agent, user, conversation) or []
        
        buttons = [
            {"label": " Revenue by Doctor", "action": "Show revenue by doctor", "variant": "primary"},
            {"label": " Busiest Doctor", "action": "Who is the busiest doctor?", "variant": "secondary"},
            {"label": " Patient Cities", "action": "Which city has the most patients?", "variant": "secondary"},
            {"label": " Unpaid Bills", "action": "Show unpaid invoices", "variant": "danger"}
        ]
        
        components.append(RichTextComponent(content="###  Quick Insights"))
        components.append(ButtonGroupComponent(buttons=buttons, orientation="horizontal"))
        return components
    
def get_llm_service():
    google_api_key = os.getenv("GOOGLE_API_KEY")
    if google_api_key:
        
        from vanna.integrations.openai import OpenAILlmService
        return OpenAILlmService(
            api_key=google_api_key,
            model="gemini-2.5-flash",
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
        )

    raise ValueError(" Check GOOGLE_API_KEY")


llm = get_llm_service()

agent_memory = DemoAgentMemory(max_items=1000)
db_tool = RunSqlTool(sql_runner=ValidatedSqliteRunner(database_path="clinic.db"))


tools = ToolRegistry()
tools.register_local_tool(db_tool, access_groups=['admin', 'user'])
tools.register_local_tool(VisualizeDataTool(), access_groups=['admin', 'user'])
tools.register_local_tool(SaveQuestionToolArgsTool(), access_groups=['admin'])

tools.register_local_tool(SearchSavedCorrectToolUsesTool(), access_groups=['admin', 'user'])


class SingleUserResolver(UserResolver):
    async def resolve_user(self, request_context: RequestContext) -> User:
        return User(id="admin", email="admin@clinic.com", group_memberships=['admin'])


agent = Agent(
    llm_service=llm,
    tool_registry=tools,
    user_resolver=SingleUserResolver(),
    agent_memory=agent_memory,
    workflow_handler=ClinicDashboardHandler()
)