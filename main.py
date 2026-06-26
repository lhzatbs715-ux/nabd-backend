from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import random
from datetime import datetime, timedelta
import jwt
import uvicorn

app = FastAPI()

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SECRET_KEY = "my-super-secret-key-12345"

class LoginRequest(BaseModel):
    username: str
    password: str

def create_token(username: str, role: str) -> str:
    payload = {"username": username, "role": role}
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing token")
    try:
        token = authorization.replace("Bearer ", "")
        return jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

# ============================================================
# ✅ المسارات الصحيحة (بدون /api/ في التعريف)
# ============================================================

@app.get("/api/health")
async def health():
    return {"status": "ok", "message": "Backend is running", "timestamp": datetime.now().isoformat()}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    if req.username == "admin" and req.password == "admin123":
        token = create_token(req.username, "superadmin")
        return {
            "success": True,
            "access_token": token,
            "user": {
                "id": 1,
                "username": "admin",
                "full_name": "مدير النظام",
                "role": "superadmin",
                "is_active": True,
                "expires_at": None
            }
        }
    raise HTTPException(status_code=401, detail="اسم المستخدم أو كلمة المرور غير صحيحة")

@app.get("/api/auth/me")
async def get_current_user(payload: dict = Depends(verify_token)):
    return {
        "id": 1,
        "username": payload.get("username"),
        "full_name": "مدير النظام",
        "role": "superadmin",
        "is_active": True,
        "expires_at": None
    }

@app.get("/api/routers")
async def get_routers(payload: dict = Depends(verify_token)):
    return [
        {"id": 1, "name": "راوتر رئيسي", "host": "192.168.1.1", "port": 8728, "location": "الرياض", "is_active": True},
        {"id": 2, "name": "راوتر فرعي", "host": "192.168.2.1", "port": 8728, "location": "جدة", "is_active": True},
    ]

@app.get("/api/stats/daily/{router_id}")
async def get_daily_stats(router_id: int, stat_date: Optional[str] = None, payload: dict = Depends(verify_token)):
    if not stat_date:
        stat_date = datetime.now().strftime("%Y-%m-%d")
    
    levels = ["high", "medium", "low", "inactive"]
    vlans = []
    for i in range(random.randint(5, 15)):
        vlans.append({
            "vlan_number": 100 + i,
            "vlan_name": f"VLAN_{100+i}",
            "gb_total": round(random.uniform(0.5, 50), 3),
            "consumption_level": levels[random.randint(0, 3)],
            "comment": ""
        })
    
    return {
        "total_gb": round(random.uniform(10, 200), 2),
        "vlan_count": len(vlans),
        "high_count": sum(1 for v in vlans if v["consumption_level"] == "high"),
        "zero_count": sum(1 for v in vlans if v["consumption_level"] == "inactive"),
        "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "vlans": vlans
    }

@app.get("/api/system/status")
async def get_system_status(payload: dict = Depends(verify_token)):
    return {
        "cpu_percent": random.randint(5, 60),
        "memory": {"percent": random.randint(20, 80), "used_gb": round(random.uniform(2, 8), 1), "total_gb": 16},
        "disk": {"percent": random.randint(30, 70), "used_gb": round(random.uniform(20, 50), 1), "total_gb": 100},
        "uptime": "3 أيام و 12 ساعة",
        "docker": {"running": 2, "total": 2}
    }

@app.get("/api/system/notifications")
async def get_notifications(payload: dict = Depends(verify_token)):
    return [
        {"id": 1, "title": "تم إضافة راوتر جديد", "body": "تم إضافة راوتر Main-Router", "type": "router", "priority": "low", "created_at": datetime.now().isoformat()},
        {"id": 2, "title": "استهلاك عالي", "body": "VLAN 110 تجاوز 50 GB", "type": "expiry", "priority": "high", "created_at": datetime.now().isoformat()}
    ]

@app.get("/api/users")
async def get_users(payload: dict = Depends(verify_token)):
    return [
        {"id": 1, "username": "admin", "full_name": "مدير النظام", "phone": "0500000000", "role": "superadmin", "is_active": True},
        {"id": 2, "username": "user1", "full_name": "مستخدم تجريبي", "phone": "0511111111", "role": "viewer", "is_active": True}
    ]

# ============================================================
# ❌ إذا لم يجد المسار
# ============================================================
@app.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE"])
async def catch_all(path: str):
    return {"error": f"المسار غير موجود: {path}"}
