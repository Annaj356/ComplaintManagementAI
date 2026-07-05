import os
import logging
import requests
from fastapi import FastAPI, HTTPException, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from typing import Literal
import bcrypt
import mysql.connector
from dotenv import load_dotenv

import ai_service
from database import get_connection
from auth import create_token, get_current_user, require_admin

from auth import (
    create_token,
    get_current_user,
    require_admin,
    create_action_token,
    verify_action_token,
)

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
BASE_URL = os.getenv("BASE_URL")
N8N_WEBHOOK_URL = os.getenv(
    "N8N_WEBHOOK_URL",
    "https://jefrymammen.app.n8n.cloud/webhook/complaint-email",
)
N8N_STATUS_WEBHOOK_URL = os.getenv("N8N_STATUS_WEBHOOK_URL")
N8N_SHARED_SECRET = os.getenv("N8N_SHARED_SECRET")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten to your real frontend URL in production
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# DB CONNECTION (per-request)
# =========================
def get_db():
    conn = get_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        yield conn, cursor
    finally:
        cursor.close()
        conn.close()


# =========================
# REQUEST/RESPONSE MODELS
# =========================
class SignupRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr
    password: str = Field(min_length=8, max_length=72)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ComplaintRequest(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)
    location: str = Field(min_length=1, max_length=100)
    # user_id intentionally NOT here — derived from the verified JWT instead


class StatusUpdateRequest(BaseModel):
    status: Literal["Submitted", "In Progress", "Resolved", "Rejected"]


# =========================
# HOME
# =========================
@app.get("/")
def home():
    return {"message": "Complaint Management AI Backend Running"}


# =========================
# SIGNUP
# =========================
@app.post("/signup", status_code=201)
def signup(data: SignupRequest, db=Depends(get_db)):
    conn, cursor = db
    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt())

    try:
        cursor.execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (data.name, data.email, hashed),
        )
        conn.commit()
    except mysql.connector.IntegrityError:
        raise HTTPException(status_code=409, detail="Email already registered")
    except mysql.connector.Error as e:
        logger.error(f"Signup DB error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    logger.info(f"New user signed up: {data.email}")
    return {"message": "User created successfully"}


# =========================
# LOGIN
# =========================
@app.post("/login")
def login(data: LoginRequest, db=Depends(get_db)):
    conn, cursor = db
    cursor.execute("SELECT * FROM users WHERE email=%s", (data.email,))
    user = cursor.fetchone()

    invalid_creds = HTTPException(status_code=401, detail="Invalid email or password")

    if not user:
        raise invalid_creds

    if not bcrypt.checkpw(
        data.password.encode(),
        user["password_hash"].encode() if isinstance(user["password_hash"], str) else user["password_hash"],
    ):
        raise invalid_creds

    token = create_token(user_id=user["id"], role=user["role"])
    logger.info(f"User logged in: {data.email}")

    return {
        "message": "Login successful",
        "access_token": token,
        "token_type": "bearer",
        "role": user["role"],
    }


# =========================
# WHO AM I
# =========================
@app.get("/me")
def get_me(current_user: dict = Depends(get_current_user), db=Depends(get_db)):
    conn, cursor = db
    cursor.execute(
        "SELECT id, name, email, role FROM users WHERE id=%s",
        (current_user["user_id"],),
    )
    user = cursor.fetchone()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


# =========================
# N8N NOTIFICATIONS (BACKGROUND TASKS)
# =========================
def send_n8n_notification(user: dict, title: str, location: str, department: str, priority: str, complaint_id: int):
    departmentemail_map = {
        "Maintenance Team": "jefrymammen3065@gmail.com",
        "IT Cell": "jefrymammen.b23cs1235@mbcet.ac.in",
        "Civil Maintenance": "annajose.b23cs1215@mbcet.ac.in",
        "Estate Office": "krishnavenideepak.b23cs1240@mbcet.ac.in",
        "Housekeeping": "krishnarajeev.b23cs1239@mbcet.ac.in"
    }

    department_email = departmentemail_map.get(department)

    in_progress_token = create_action_token(complaint_id, "In Progress")
    resolved_token = create_action_token(complaint_id, "Resolved")
    in_progress_link = f"{BASE_URL}/update-status-link?token={in_progress_token}"
    resolved_link = f"{BASE_URL}/update-status-link?token={resolved_token}"

    try:
        logger.info(f"Sending complaint #{complaint_id} to n8n...")
        response = requests.post(
        N8N_WEBHOOK_URL,
        headers={"X-Webhook-Secret": N8N_SHARED_SECRET},
        json={
            "name": user["name"],
            "email": user["email"],
            "title": title,
            "location": location,
            "department": department,
            "priority": priority,
            "complaint_id": complaint_id,
            "department_email": department_email,
            "in_progress_link": in_progress_link,
            "resolved_link": resolved_link,
        },
        timeout=10,
    )
        logger.info(f"n8n response — status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"n8n notification failed for complaint #{complaint_id}: {e}")


def send_status_update_notification(
    student_email: str, student_name: str, title: str, complaint_id: int, new_status: str
):
    if not N8N_STATUS_WEBHOOK_URL:
        logger.error("N8N_STATUS_WEBHOOK_URL not set — skipping status notification")
        return

    try:
        logger.info(f"Sending status update for complaint #{complaint_id} to student...")
        response = requests.post(
            N8N_STATUS_WEBHOOK_URL,
            headers={"X-Webhook-Secret": N8N_SHARED_SECRET},
            json={
                "student_name": student_name,
                "student_email": student_email,
                "title": title,
                "complaint_id": complaint_id,
                "new_status": new_status,
            },
            timeout=10,
        )
        logger.info(f"n8n status-update response — status {response.status_code}: {response.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"n8n status-update notification failed for complaint #{complaint_id}: {e}")

    

# =========================
# CREATE COMPLAINT (AI POWERED)
# =========================
@app.post("/complaint", status_code=201)
def create_complaint(
    data: ComplaintRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conn, cursor = db
    user_id = current_user["user_id"]  # trusted — from verified token, not client input

    cursor.execute("SELECT name, email FROM users WHERE id=%s", (user_id,))
    user = cursor.fetchone()

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    try:
        ai = ai_service.classify_complaint(data.description)
    except Exception as e:
        logger.error(f"AI classification failed: {e}")
        raise HTTPException(status_code=502, detail=f"AI classification failed: {e}")

    try:
        cursor.execute(
            """
            INSERT INTO complaints
            (user_id, title, description, location, category, priority, department, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """,
            (
                user_id,
                data.title,
                data.description,
                data.location,
                ai["category"],
                ai["priority"],
                ai["department"],
                "Submitted",
            ),
        )
        conn.commit()
        new_id = cursor.lastrowid
    except mysql.connector.Error as e:
        logger.error(f"Complaint insert DB error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {e}")

    logger.info(f"Complaint #{new_id} created by user {user_id}: {data.title}")

    background_tasks.add_task(
        send_n8n_notification,
        user, data.title, data.location, ai["department"], ai["priority"], new_id
    )

    return {
        "message": "Complaint submitted",
        "complaint_id": new_id,
        "ai_result": ai,
    }


# =========================
# GET ALL COMPLAINTS
# =========================
@app.get("/complaints")
def get_complaints(
    limit: int = 50,
    offset: int = 0,
    db=Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    conn, cursor = db
    cursor.execute(
        "SELECT * FROM complaints ORDER BY id DESC LIMIT %s OFFSET %s",
        (limit, offset),
    )
    return cursor.fetchall()


# =========================
# UPDATE STATUS (ADMIN ONLY)
# =========================
@app.put("/complaint/{id}")
def update_status(
    id: int,
    data: StatusUpdateRequest,
    background_tasks: BackgroundTasks,
    db=Depends(get_db),
    current_user: dict = Depends(require_admin),
):
    conn, cursor = db

    # Fetch complaint + student info BEFORE updating, so we know who to notify
    cursor.execute(
        """
        SELECT c.title, u.email AS student_email, u.name AS student_name
        FROM complaints c
        JOIN users u ON c.user_id = u.id
        WHERE c.id = %s
        """,
        (id,),
    )
    complaint = cursor.fetchone()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    cursor.execute("UPDATE complaints SET status=%s WHERE id=%s", (data.status, id))
    conn.commit()

    logger.info(f"Complaint #{id} status updated to '{data.status}' by admin {current_user['user_id']}")

    # Fire-and-forget — notify the student their status changed
    background_tasks.add_task(
        send_status_update_notification,
        complaint["student_email"],
        complaint["student_name"],
        complaint["title"],
        id,
        data.status,
    )

    return {"message": "Status updated"}
