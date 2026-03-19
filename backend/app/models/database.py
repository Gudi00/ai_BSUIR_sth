from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, Float, DateTime, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from datetime import datetime
import enum
import os

# Database Configuration
DATABASE_URL = "sqlite:///./data/natasha.db"
os.makedirs("data", exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class DiffType(str, enum.Enum):
    EQUAL = "equal"
    CHANGED = "changed"
    ADDED = "added"
    DELETED = "deleted"
    SPLIT = "split"
    MERGE = "merge"

class RiskLevel(str, enum.Enum):
    GREEN = "green"
    YELLOW = "yellow"
    RED = "red"

class Document(Base):
    __tablename__ = "documents"
    
    id = Column(String, primary_key=True)
    filename = Column(String, nullable=False)
    file_path = Column(String, nullable=False)
    upload_date = Column(DateTime, default=datetime.utcnow)
    file_type = Column(String)  # docx, pdf
    
    blocks = relationship("DocumentBlock", back_populates="document", cascade="all, delete-orphan")

class DocumentBlock(Base):
    __tablename__ = "document_blocks"
    
    id = Column(String, primary_key=True)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)
    number = Column(String)
    heading = Column(String)
    raw_text = Column(Text, nullable=False)
    clean_text = Column(Text)
    lemma_text = Column(Text)
    position = Column(Integer)  # Порядок в документе
    path = Column(String)  # Иерархический путь (напр. "Раздел 1 > Пункт 1.1")
    hierarchy_level = Column(Integer, default=10)
    
    document = relationship("Document", back_populates="blocks")

class ComparisonJob(Base):
    __tablename__ = "comparison_jobs"
    
    id = Column(String, primary_key=True)
    old_doc_id = Column(String, ForeignKey("documents.id"))
    new_doc_id = Column(String, ForeignKey("documents.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="completed")
    
    alignments = relationship("BlockAlignment", back_populates="job", cascade="all, delete-orphan")

class BlockAlignment(Base):
    __tablename__ = "block_alignments"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(String, ForeignKey("comparison_jobs.id"), nullable=False)
    old_block_id = Column(String, ForeignKey("document_blocks.id"), nullable=True)
    new_block_id = Column(String, ForeignKey("document_blocks.id"), nullable=True)
    
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.GREEN)
    risk_explanation = Column(Text)
    diff_type = Column(Enum(DiffType), default=DiffType.EQUAL)
    score = Column(Float, default=1.0)
    
    job = relationship("ComparisonJob", back_populates="alignments")
    old_block = relationship("DocumentBlock", foreign_keys=[old_block_id])
    new_block = relationship("DocumentBlock", foreign_keys=[new_block_id])

def init_db():
    Base.metadata.create_all(bind=engine)
