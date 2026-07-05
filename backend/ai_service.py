<<<<<<< HEAD
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# pydantic-ai reads GROQ_API_KEY from the environment automatically —
# just make sure it's set in your .env file.
if not os.getenv("GROQ_API_KEY"):
    logger.error("GROQ_API_KEY not set — check your .env file")


# =========================
# 1. STRUCTURED OUTPUT SCHEMA
# =========================
class ComplaintOutput(BaseModel):
    category: str
    priority: str


MODEL = "groq:llama-3.3-70b-versatile"  # pydantic-ai's provider:model format

SYSTEM_PROMPT = """
You are an AI system for a college complaint management system.
Analyze the complaint and classify it.

CATEGORIES:
- Electrical
- IT Support
- Plumbing
- Infrastructure
- Cleaning
- Canteen
- Other

PRIORITY RULES:
- Critical: danger, fire, electric shock, safety risk
- High: major system failure or blocking work
- Medium: partial issue or inconvenience
- Low: minor issue
"""

agent = Agent(
    MODEL,
    output_type=ComplaintOutput,
    system_prompt=SYSTEM_PROMPT,
)


# =========================
# 2. RULE-BASED DEPARTMENT MAP
# =========================
DEPARTMENT_MAP = {
    "Electrical": "Maintenance Team",
    "IT Support": "IT Cell",
    "Plumbing": "Civil Maintenance",
    "Infrastructure": "Estate Office",
    "Cleaning": "Housekeeping",
    "Canteen": "Canteen Management",
    "Other": "General Administration",
}

VALID_CATEGORIES = set(DEPARTMENT_MAP.keys())
VALID_PRIORITIES = {"Critical", "High", "Medium", "Low"}

FALLBACK_RESULT = ComplaintOutput(category="Other", priority="Low")


# =========================
# 3. CALL LLM (via pydantic-ai)
# =========================
def call_llm(text: str) -> ComplaintOutput:
    try:
        result = agent.run_sync(f"Complaint: {text}")
        return result.output  # already a validated ComplaintOutput instance
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return FALLBACK_RESULT


# =========================
# 4. FINAL PROCESSING LOGIC
# =========================
def classify_complaint(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Complaint text cannot be empty")

    # Step 1: Get structured AI output (already type-validated by pydantic-ai)
    ai_result = call_llm(text)

    # Step 2: Validate against known enums (LLM can still hallucinate string values
    # even inside a valid schema, so don't skip this)
    category = ai_result.category if ai_result.category in VALID_CATEGORIES else "Other"
    if category != ai_result.category:
        logger.warning(f"LLM returned unknown category '{ai_result.category}', defaulting to 'Other'")

    priority = ai_result.priority if ai_result.priority in VALID_PRIORITIES else "Low"
    if priority != ai_result.priority:
        logger.warning(f"LLM returned unknown priority '{ai_result.priority}', defaulting to 'Low'")

    # Step 3: RULE ENGINE — deterministic department routing
    department = DEPARTMENT_MAP.get(category, "General Administration")

    # Step 4: Final structured output
    return {
        "category": category,
        "priority": priority,
        "department": department,
    }


# =========================
# 5. Example usage
# =========================
if __name__ == "__main__":
    sample_complaint = "There's a sparking wire near the hostel entrance, it's dangerous."
=======
import os
import logging
from dotenv import load_dotenv
from pydantic import BaseModel
from pydantic_ai import Agent

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# pydantic-ai reads GROQ_API_KEY from the environment automatically —
# just make sure it's set in your .env file.
if not os.getenv("GROQ_API_KEY"):
    logger.error("GROQ_API_KEY not set — check your .env file")


# =========================
# 1. STRUCTURED OUTPUT SCHEMA
# =========================
class ComplaintOutput(BaseModel):
    category: str
    priority: str


MODEL = "groq:llama-3.3-70b-versatile"  # pydantic-ai's provider:model format

SYSTEM_PROMPT = """
You are an AI system for a college complaint management system.
Analyze the complaint and classify it.

CATEGORIES:
- Electrical
- IT Support
- Plumbing
- Infrastructure
- Cleaning
- Canteen
- Other

PRIORITY RULES:
- Critical: danger, fire, electric shock, safety risk
- High: major system failure or blocking work
- Medium: partial issue or inconvenience
- Low: minor issue
"""

agent = Agent(
    MODEL,
    output_type=ComplaintOutput,
    system_prompt=SYSTEM_PROMPT,
)


# =========================
# 2. RULE-BASED DEPARTMENT MAP
# =========================
DEPARTMENT_MAP = {
    "Electrical": "Maintenance Team",
    "IT Support": "IT Cell",
    "Plumbing": "Civil Maintenance",
    "Infrastructure": "Estate Office",
    "Cleaning": "Housekeeping",
    "Canteen": "Canteen Management",
    "Other": "General Administration",
}

VALID_CATEGORIES = set(DEPARTMENT_MAP.keys())
VALID_PRIORITIES = {"Critical", "High", "Medium", "Low"}

FALLBACK_RESULT = ComplaintOutput(category="Other", priority="Low")


# =========================
# 3. CALL LLM (via pydantic-ai)
# =========================
def call_llm(text: str) -> ComplaintOutput:
    try:
        result = agent.run_sync(f"Complaint: {text}")
        return result.output  # already a validated ComplaintOutput instance
    except Exception as e:
        logger.error(f"LLM call failed: {e}")
        return FALLBACK_RESULT


# =========================
# 4. FINAL PROCESSING LOGIC
# =========================
def classify_complaint(text: str) -> dict:
    if not text or not text.strip():
        raise ValueError("Complaint text cannot be empty")

    # Step 1: Get structured AI output (already type-validated by pydantic-ai)
    ai_result = call_llm(text)

    # Step 2: Validate against known enums (LLM can still hallucinate string values
    # even inside a valid schema, so don't skip this)
    category = ai_result.category if ai_result.category in VALID_CATEGORIES else "Other"
    if category != ai_result.category:
        logger.warning(f"LLM returned unknown category '{ai_result.category}', defaulting to 'Other'")

    priority = ai_result.priority if ai_result.priority in VALID_PRIORITIES else "Low"
    if priority != ai_result.priority:
        logger.warning(f"LLM returned unknown priority '{ai_result.priority}', defaulting to 'Low'")

    # Step 3: RULE ENGINE — deterministic department routing
    department = DEPARTMENT_MAP.get(category, "General Administration")

    # Step 4: Final structured output
    return {
        "category": category,
        "priority": priority,
        "department": department,
    }


# =========================
# 5. Example usage
# =========================
if __name__ == "__main__":
    sample_complaint = "There's a sparking wire near the hostel entrance, it's dangerous."
>>>>>>> 45d8bc0121f9aff758b3155930da15098b4028af
    print(classify_complaint(sample_complaint))