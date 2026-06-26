from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import asyncpg
import os
import json
import random
from datetime import datetime, timedelta
import bcrypt
import jwt
import uvicorn

# ============================================================
# إعدادات التطبيق
# ============================================================
app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ============================================================
# إعدادات قاعدة البيانات (PostgreSQL)
# ============================================================
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:pass@localhost/db")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")

# ============================================================
# النماذج (Pydantic)
# ============================================================
class LoginRequest(BaseModel):
    username: str
    password: str

class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    is_active: bool

class RouterResponse(BaseModel):
    id: int
    name: str
    host: str
    port: int
    location: str
    is_active: bool

class VLanData(BaseModel):
    vlan_number: int
    vlan_name: str
    total_gb: float
    consumption_level: str
    comment: str

# ============================================================
# دوال مساعدة
# ============================================================
async def get_db():
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        yield conn
    finally:
        await conn.close()

def create_token(username: str, role: str) -> str:
    payload = {"username": username, "role": role}
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token

def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        token = authorization.replace("Bearer ", "")
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============================================================
# المسارات (Endpoints)
# ============================================================

# ---- الصحة ----
@app.get("/api/health")
async def health():
    return {"status": "ok", "timestamp": datetime.now().isoformat()}

# ---- تسجيل الدخول ----
@app.post("/api/auth/login")
async def login(req: LoginRequest, conn: asyncpg.Connection = Depends(get_db)):
    try:
        user = await conn.fetchrow(
            "SELECT id, username, full_name, password_hash, role, is_active, expires_at FROM users WHERE username = $1",
            req.username
        )
        if user:
            stored_hash = user['password_hash']
            if bcrypt.checkpw(req.password.encode('utf-8'), stored_hash.encode('utf-8')):
                token = create_token(user['username'], user['role'])
                return {
                    "success": True,
                    "access_token": token,
                    "user": {
                        "id": user['id'],
                        "username": user['username'],
                        "full_name": user['full_name'],
                        "role": user['role'],
                        "is_active": user['is_active'],
                        "expires_at": user['expires_at']
                    }
                }
        raise HTTPException(status_code=401, detail="اسم المستخدم أو كلمة المرور غير صحيحة")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- بيانات المستخدم ----
@app.get("/api/auth/me")
async def get_current_user(payload: dict = Depends(verify_token), conn: asyncpg.Connection = Depends(get_db)):
    try:
        user = await conn.fetchrow(
            "SELECT id, username, full_name, role, is_active, expires_at FROM users WHERE username = $1",
            payload.get("username")
        )
        if user:
            return dict(user)
        raise HTTPException(status_code=404, detail="المستخدم غير موجود")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- الراوترات ----
@app.get("/api/routers")
async def get_routers(payload: dict = Depends(verify_token), conn: asyncpg.Connection = Depends(get_db)):
    try:
        routers = await conn.fetch("SELECT * FROM routers ORDER BY id DESC")
        return [dict(r) for r in routers]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---- إحصائيات يومية ----
@app.get("/api/stats/daily/{router_id}")
async def get_daily_stats(router_id: int, stat_date: str = None, payload: dict = Depends(verify_token)):
    if not stat_date:
        stat_date = datetime.now().strftime("%Y-%m-%d")
    
    # محاكاة بيانات (Mock)
    total_gb = random.randint(10, 200)
    vlan_count = random.randint(20, 80)
    high_count = random.randint(1, 10)
    zero_count = random.randint(0, 5)
    
    vlans = []
    for i in range(random.randint(5, 15)):
        levels = ["high", "medium", "low", "inactive"]
        vlans.append({
            "vlan_number": 100 + i,
            "vlan_name": f"VLAN_{100+i}",
            "gb_total": round(random.uniform(1, 50), 3),
            "consumption_level": levels[random.randint(0, 3)],
            "comment": ""
        })
    
    return {
        "total_gb": total_gb,
        "vlan_count": vlan_count,
        "high_count": high_count,
        "zero_count": zero_count,
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vlans": vlans
    }

# ---- إحصائيات شهرية ----
@app.get("/api/stats/monthly/{router_id}")
async def get_monthly_stats(router_id: int, year: str = None, month: str = None, payload: dict = Depends(verify_token)):
    if not year:
        year = datetime.now().strftime("%Y")
    if not month:
        month = datetime.now().strftime("%m")
    
    days = []
    for i in range(30):
        days.append({
            "date": (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d"),
            "total_in": round(random.uniform(5, 100), 3),
            "total_out": round(random.uniform(5, 100), 3),
            "total_gb": round(random.uniform(10, 200), 3),
            "vlan_count": random.randint(20, 60)
        })
    
    return {
        "days": days,
        "grand_total_gb": round(random.uniform(500, 2000), 2)
    }

# ---- حالة النظام ----
@app.get("/api/system/status")
async def get_system_status(payload: dict = Depends(verify_token)):
    return {
        "cpu_percent": random.randint(5, 60),
        "memory": {
            "percent": random.randint(20, 80),
            "used_gb": round(random.uniform(2, 8), 1),
            "total_gb": 16
        },
        "disk": {
            "percent": random.randint(30, 70),
            "used_gb": round(random.uniform(20, 50), 1),
            "total_gb": 100
        },
        "uptime": "3 أيام و 12 ساعة",
        "docker": {"running": 2, "total": 2}
    }

# ---- التنبيهات ----
@app.get("/api/system/notifications")
async def get_notifications(payload: dict = Depends(verify_token)):
    return [
        {"id": 1, "title": "تم إضافة راوتر جديد", "body": "تم إضافة راوتر Main-Router", "type": "router", "priority": "low", "created_at": datetime.now().isoformat()},
        {"id": 2, "title": "استهلاك عالي", "body": "VLAN 110 تجاوز 50 GB", "type": "expiry", "priority": "high", "created_at": datetime.now().isoformat()}
    ]

# ============================================================
# تشغيل التطبيق
# ============================================================
if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)