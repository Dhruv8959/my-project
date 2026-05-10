import os
from contextlib import asynccontextmanager

import shutil
import uuid
from fastapi import FastAPI, UploadFile, File, HTTPException, Query, BackgroundTasks
from fastapi.responses import FileResponse, JSONResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from video_processor import process_video

# --- DB & Auth Imports ---
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List
from datetime import datetime, timedelta
import random

from database import engine, Base, get_db
import models
import auth
from pydantic import BaseModel

# Create DB tables
Base.metadata.create_all(bind=engine)
# -----------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Setup default users and dummy data if DB is empty
    db = next(get_db())
    
    # --- AUTOMATIC MIGRATION (Add missing columns for SQLite) ---
    from sqlalchemy import text
    # Add job_id
    try:
        db.execute(text("ALTER TABLE job_logs ADD COLUMN job_id VARCHAR"))
        db.commit()
    except Exception:
        db.rollback()
    
    # Add status
    try:
        db.execute(text("ALTER TABLE job_logs ADD COLUMN status VARCHAR DEFAULT 'COMPLETED'"))
        db.commit()
    except Exception:
        db.rollback()


    # 1. Ensure admin exists
    admin_user = db.query(models.User).filter(models.User.username == "admin").first()
    if not admin_user:
        hashed_pw = auth.get_password_hash("admin")
        admin_user = models.User(username="admin", hashed_password=hashed_pw, role="admin")
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)
        
    # 2. Ensure operator exists
    user1 = db.query(models.User).filter(models.User.username == "operator1").first()
    if not user1:
        user1 = models.User(username="operator1", hashed_password=auth.get_password_hash("pass123"), role="user")
        db.add(user1)
        db.commit()
        db.refresh(user1)

    # 3. Populate logs if empty
    log_count = db.query(models.JobLog).count()
    if log_count == 0:
        shifts = ["Morning", "Evening", "Night"]
        for i in range(20):
            job_uid = str(uuid.uuid4())[:8]
            log = models.JobLog(
                job_id=job_uid,
                user_id=random.choice([admin_user.id, user1.id]),
                shift=random.choice(shifts),
                timestamp=datetime.utcnow() - timedelta(hours=random.randint(1, 100)),
                video_filename=f"factory_processing_{i}.mp4",
                bag_count=random.randint(45, 550),
                status="COMPLETED"
            )
            db.add(log)
        db.commit()
        
    db.close()
    yield




app = FastAPI(
    title="CementVision Bag Counter API",
    description="Upload a video to count cement bags. Returns a CSV report.",
    version="3.0",
    lifespan=lifespan
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = "uploads"
OUTPUT_DIR = "outputs"
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)



# Mount frontend directory
app.mount("/frontend", StaticFiles(directory="frontend"), name="frontend")


@app.get("/")
def default_page():
    """Default landing page - Dashboard"""
    return FileResponse("frontend/results_gallery.html")



@app.get("/login")
def login_page():
    return FileResponse("frontend/admin_login.html")

@app.get("/live")
def live_page():
    return FileResponse("frontend/live_processing.html")

@app.get("/report")
def report_page():
    return FileResponse("frontend/detailed_reports.html")

@app.get("/shifts")
def shift_dashboard_page():
    return FileResponse("frontend/shift_logs.html")

@app.get("/settings")
def settings_page():
    return FileResponse("frontend/settings.html")

@app.get("/health")
def health_page():
    return FileResponse("frontend/shift_logs.html")





# --- API ROUTES ---

class Token(BaseModel):
    access_token: str
    token_type: str
    role: str

@app.post("/api/login", response_model=Token)
def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer", "role": user.role}

@app.get("/api/logs")
def get_job_logs(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Return all logs if admin, otherwise only the user's logs."""
    if current_user.role == "admin":
        logs = db.query(models.JobLog).order_by(models.JobLog.timestamp.desc()).all()
    else:
        logs = db.query(models.JobLog).filter(models.JobLog.user_id == current_user.id).order_by(models.JobLog.timestamp.desc()).all()
    
    # Format for JSON
    result = []
    for log in logs:
        user = db.query(models.User).filter(models.User.id == log.user_id).first()
        result.append({
            "id": log.id,
            "job_id": log.job_id or f"LEGACY-{log.id}",
            "username": user.username if user else "Unknown",
            "shift": log.shift,
            "timestamp": log.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            "video": log.video_filename,
            "bags": log.bag_count or 0,
            "status": log.status or "COMPLETED"
        })
    return result


@app.get("/api/shifts")
def get_shift_summary(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Return total bag counts grouped by shift."""
    if current_user.role == "admin":
        summary = db.query(models.JobLog.shift, func.sum(models.JobLog.bag_count).label('total_bags')).group_by(models.JobLog.shift).all()
    else:
        summary = db.query(models.JobLog.shift, func.sum(models.JobLog.bag_count).label('total_bags')).filter(models.JobLog.user_id == current_user.id).group_by(models.JobLog.shift).all()
    
    return [{"shift": row.shift, "total_bags": row.total_bags or 0} for row in summary]

@app.get("/api/system/status")
def get_system_status(current_user: models.User = Depends(auth.get_current_user)):
    """Return system health and RTSP stream status."""
    return {
        "rtsp_status": "ACTIVE",
        "rtsp_stream": "rtsp://factory-cam-01:554/live",
        "cpu_usage": "42%",
        "uptime": "142h 12m",
        "sensors": "OPERATIONAL"
    }





def get_current_shift():
    """Determine the current shift based on the time of day."""
    hour = datetime.now().hour
    if 6 <= hour < 14:
        return "Morning"
    elif 14 <= hour < 22:
        return "Evening"
    else:
        return "Night"

def run_video_processing(job_id: str, save_path: str, frame_skip: int, confidence: float, filename: str):
    """Background task to process video and update database."""
    db = next(get_db())
    try:
        # Update status to PROCESSING
        db_log = db.query(models.JobLog).filter(models.JobLog.job_id == job_id).first()
        if db_log:
            db_log.status = "PROCESSING"
            db.commit()

        result = process_video(
            video_path=save_path,
            output_dir=OUTPUT_DIR,
            frame_skip=frame_skip,
            confidence=confidence,
            job_id=job_id
        )
        
        # Update status to COMPLETED
        if db_log:
            db_log.bag_count = result["total_unique_bags"]
            db_log.status = "COMPLETED"
            db.commit()

    except Exception as e:
        print(f"[ERROR] Job {job_id} failed: {str(e)}")
        db_log = db.query(models.JobLog).filter(models.JobLog.job_id == job_id).first()
        if db_log:
            db_log.status = "FAILED"
            db.commit()
    finally:
        if os.path.exists(save_path):
            os.remove(save_path)
        db.close()

@app.post("/upload/")
def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    frame_skip: int = Query(default=2, ge=1, le=10),
    confidence: float = Query(default=0.4, ge=0.1, le=0.95),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Upload a video file and start background processing.
    """
    job_id    = str(uuid.uuid4())[:8]
    ext       = os.path.splitext(file.filename)[1].lower()
    save_path = os.path.join(UPLOAD_DIR, f"{job_id}{ext}")

    with open(save_path, "wb") as buf:
        shutil.copyfileobj(file.file, buf)

    # 1. Create Pending Log
    new_log = models.JobLog(
        job_id=job_id,
        user_id=current_user.id,
        shift=get_current_shift(),
        timestamp=datetime.utcnow(),
        video_filename=file.filename,
        bag_count=0,
        status="PENDING"
    )
    db.add(new_log)
    db.commit()

    # 2. Add Background Task
    background_tasks.add_task(
        run_video_processing, 
        job_id, save_path, frame_skip, confidence, file.filename
    )

    return JSONResponse({
        "job_id": job_id,
        "message": "Upload successful. Processing started in background.",
        "status": "PENDING"
    })

@app.get("/api/job/{job_id}")
def get_job_status(job_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)):
    """Check the status and details of a processing job."""
    job = db.query(models.JobLog).filter(models.JobLog.job_id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    
    # Check permissions
    if current_user.role != "admin" and job.user_id != current_user.id:
        raise HTTPException(403, "Access denied")
    
    return {
        "job_id": job.job_id,
        "status": job.status,
        "bag_count": job.bag_count,
        "video": job.video_filename,
        "timestamp": job.timestamp.strftime("%Y-%m-%d %H:%M:%S")
    }





@app.get("/download/csv/{job_id}")
def download_csv(job_id: str):
    """Download the per-frame CSV report for a specific job."""
    csv_filename = f"{job_id}_bag_count.csv"
    path = os.path.join(OUTPUT_DIR, csv_filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="text/csv",
                            filename=f"cement_bag_report_{job_id}.csv")
    
    # Fallback for older naming convention if any
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith(job_id) and fname.endswith(".csv"):
            path = os.path.join(OUTPUT_DIR, fname)
            return FileResponse(path, media_type="text/csv",
                                filename=f"cement_bag_report_{job_id}.csv")
            
    raise HTTPException(404, f"CSV for Job {job_id} not found.")


@app.get("/download/video/{job_id}")
def download_video(job_id: str):
    """Download the annotated output video for a specific job."""
    video_filename = f"{job_id}_annotated.mp4"
    path = os.path.join(OUTPUT_DIR, video_filename)
    if os.path.exists(path):
        return FileResponse(path, media_type="video/mp4",
                            filename=f"annotated_{job_id}.mp4")

    # Fallback
    for fname in os.listdir(OUTPUT_DIR):
        if fname.startswith(job_id) and fname.endswith(".mp4"):
            path = os.path.join(OUTPUT_DIR, fname)
            return FileResponse(path, media_type="video/mp4",
                                filename=f"annotated_{job_id}.mp4")

    raise HTTPException(404, f"Annotated video for Job {job_id} not found.")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="10.27.48.109", port=8000)
