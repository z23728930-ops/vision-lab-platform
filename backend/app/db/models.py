# app/db/models.py
from sqlalchemy import (Column, Integer, String, Boolean, TIMESTAMP, TEXT,
                        Enum, ForeignKey, JSON, Float) # TINYINT 移除了, 新增 Float
from sqlalchemy.dialects.mysql import TINYINT # 确保 TINYINT 还在，如果需要
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .base import Base
import enum


class UserRole(str, enum.Enum):
    user = "user"
    admin = "admin"


class JobStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    completed = "completed"
    failed = "failed"

# 新增：标注类型枚举
class AnnotationType(str, enum.Enum):
    bbox = "bbox"
    polygon = "polygon"
    point = "point"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user)
    created_at = Column(TIMESTAMP, server_default=func.now())
    # --- 新增字段 ---
    email = Column(String(100), unique=True, nullable=True, index=True)  # 用户的邮箱，可以为空，但如果存在则唯一
    receive_notifications = Column(Boolean, default=True)  # 是否接收邮件通知
    # ---------------


    models_uploaded = relationship("Model", back_populates="uploader")
    datasets_owned = relationship("Dataset", back_populates="owner")
    processing_jobs_submitted = relationship("ProcessingJob", back_populates="submitter") # 确保这个关系存在
    inference_results_created = relationship("InferenceResult", back_populates="creator") # 确保这个关系存在


class Model(Base):
    __tablename__ = "models"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    version = Column(String(20))
    description = Column(TEXT)
    file_path = Column(String(255), nullable=False)
    model_type = Column(String(50))
    uploaded_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())
    is_deleted = Column(Boolean, default=False)

    uploader = relationship("User", back_populates="models_uploaded")


class Dataset(Base):
    __tablename__ = "datasets"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    description = Column(TEXT)
    storage_path = Column(String(255), nullable=False)
    owner_id = Column(Integer, ForeignKey("users.id"))
    is_public = Column(Boolean, default=False)
    created_at = Column(TIMESTAMP, server_default=func.now())

    owner = relationship("User", back_populates="datasets_owned")
    images = relationship("Image", back_populates="dataset", cascade="all, delete-orphan") # 新增关系


# 新增 Image 模型
class Image(Base):
    __tablename__ = "images"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False)
    file_path = Column(String(255), nullable=False) # 绝对路径
    filename = Column(String(255), nullable=False) # 原始文件名
    created_at = Column(TIMESTAMP, server_default=func.now())

    dataset = relationship("Dataset", back_populates="images")
    annotations = relationship("Annotation", back_populates="image", cascade="all, delete-orphan") # 新增关系


# 新增 Annotation 模型
class Annotation(Base):
    __tablename__ = "annotations"
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    image_id = Column(Integer, ForeignKey("images.id"), nullable=False)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False) # 冗余字段，方便查询
    annotation_type = Column(Enum(AnnotationType), nullable=False) # bbox, polygon, point
    label = Column(String(100), nullable=False) # 标注的类别
    coordinates = Column(JSON, nullable=False) # 存储坐标数据，例如 {"x": 10, "y": 20, "width": 50, "height": 50} 或 {"points": [[x1,y1],[x2,y2]]}
    extra_data = Column(JSON, default={}) # <-- 将 'metadata' 改为 'extra_data'
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(TIMESTAMP, server_default=func.now(), onupdate=func.now())

    image = relationship("Image", back_populates="annotations")


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(Integer, primary_key=True, autoincrement=True)
    source_dataset_id = Column(Integer, ForeignKey("datasets.id"))
    output_folder_name = Column(String(255))
    processing_steps = Column(JSON)
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    progress = Column(TINYINT, default=0)
    submitted_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())

    submitter = relationship("User", back_populates="processing_jobs_submitted") # 确保这个关系存在


class InferenceResult(Base):
    __tablename__ = "inference_results"
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_name = Column(String(100))
    source_dataset_id = Column(Integer, ForeignKey("datasets.id"))
    model_id = Column(Integer, ForeignKey("models.id"))
    inference_params = Column(JSON)
    results_summary = Column(JSON)
    output_path = Column(String(255))
    status = Column(Enum(JobStatus), default=JobStatus.pending)
    created_by_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(TIMESTAMP, server_default=func.now())

    creator = relationship("User", back_populates="inference_results_created") # 确保这个关系存在