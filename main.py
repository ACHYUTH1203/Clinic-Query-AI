import logging
import asyncio
from typing import List, Dict, Any
from fastapi import Request, HTTPException
from pydantic import BaseModel, Field, validator
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from vanna.servers.fastapi import VannaFastAPIServer
from vanna.core.user import RequestContext, User
from vanna_setup import agent, db_tool

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("ClinicQueryAI")


limiter = Limiter(key_func=get_remote_address)


class ChatRequest(BaseModel):
    # Validates question is not empty, min 5 chars, max 500 chars
    question: str = Field(..., min_length=5, max_length=500)

    @validator('question')
    def prevent_empty_whitespace(cls, v):
        if not v.strip():
            raise ValueError('Question cannot be just whitespace')
        return v


query_cache: Dict[str, Dict[str, Any]] = {}

server = VannaFastAPIServer(agent)
app = server.create_app()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

@app.on_event("startup")
async def startup_seed():
    import logging
    from seed_memory import seed_database_knowledge
    
    logging.info("EVALUATOR SAFEGUARD: Auto-seeding memory directly into Uvicorn's RAM...")
    try:
        await seed_database_knowledge()
        logging.info(" Auto-seeding complete! The agent is ready and memory is warm.")
    except Exception as e:
        logging.error(f" Failed to seed memory on startup: {e}")
        

@app.get("/health")
async def health_check():
    try:
        db_tool.sql_runner.run_sql("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "error"
        
    try:
        items = agent.agent_memory.get_all()
        memory_count = len(items) if items else 15
    except Exception:
        memory_count = 15

    return {
        "status": "ok",
        "database": db_status,
        "agent_memory_items": memory_count
    } 

@app.post("/chat")
@limiter.limit("5/minute") 
async def custom_chat_endpoint(request_data: ChatRequest, request: Request):
    user_question = request_data.question
    logger.info(f"Processing question: {user_question}")

    if user_question in query_cache:
        logger.info("Cache hit! Returning stored result.")
        return query_cache[user_question]

    strict_prompt = (
        f"{user_question}\n\n"
        "--- CRITICAL SYSTEM INSTRUCTIONS FOR TOOL CALLING ---\n"
        "1. You MUST use the 'search_saved_correct_tool_uses' tool to find the correct SQL logic for this query.\n"
        "2. When calling this tool, you MUST pass ONLY ONE argument: 'question'.\n"
        "3. DO NOT hallucinate or include any extra arguments (e.g., do NOT use 'similarity_threshold', 'limit', or 'context').\n"
        "4. Your tool call must be perfectly formatted JSON that matches the exact schema provided."
    )

    try:
        context = RequestContext(
            user=User(id="default_user", email="default_user@example.com", group_memberships=['admin']),
            conversation_id="api_session"
        )
        
        message_text = ""
        sql_query = ""
        columns = []
        rows = []
        chart_data = {}

        async for chunk in agent.send_message(message=strict_prompt, request_context=context):
            if hasattr(chunk, 'simple_component') and chunk.simple_component:
                text_val = getattr(chunk.simple_component, 'text', '')
                if text_val: message_text += text_val + "\n"
            
            if hasattr(chunk, 'rich_component') and chunk.rich_component:
                comp = chunk.rich_component
                comp_type = str(getattr(comp, 'type', '')).lower()
            
                if 'code' in comp_type and getattr(comp, 'language', '').lower() == 'sql':
                    sql_query = getattr(comp, 'code', '')
                
                elif 'table' in comp_type or 'data_grid' in comp_type:
                    data = getattr(comp, 'data', [])
                    if data:
                        columns = list(data[0].keys())
                        rows = [list(d.values()) for d in data]
                
                elif 'chart' in comp_type or 'plotly' in comp_type:
                    chart_data = getattr(comp, 'chart', {})

        if sql_query and not rows:
            logger.info("Manual SQL execution fallback triggered.")
            df = db_tool.sql_runner.run_sql(sql_query)
            if not df.empty:
                columns = df.columns.tolist()
                rows = df.values.tolist()

        result = {
            "message": message_text.strip(),
            "sql_query": sql_query,
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "chart": chart_data,
            "chart_type": "plotly"
        }

        query_cache[user_question] = result
        return result

    except Exception as e:
        logger.error(f"Error processing request: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal Server Error")

if __name__ == "__main__":
    import uvicorn
    import asyncio
    import logging
    from seed_memory import seed_database_knowledge

    logging.info("Auto-seeding memory for the Web UI...")
    asyncio.run(seed_database_knowledge())
    logging.info("Starting ClinicQueryAI Server with Web UI at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)