from sqlalchemy import Column, Integer, String, DateTime
from database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    role = Column(String, default="user") # 'admin' or 'user'

class JobLog(Base):
    __tablename__ = "job_logs"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(String, unique=True, index=True)
    user_id = Column(Integer, index=True) 
    shift = Column(String, index=True)    
    timestamp = Column(DateTime, default=datetime.datetime.utcnow)
    video_filename = Column(String)
    bag_count = Column(Integer, default=0)
    status = Column(String, default="PENDING") # 'PENDING', 'PROCESSING', 'COMPLETED', 'FAILED'

