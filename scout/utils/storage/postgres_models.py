import enum
import uuid

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Table, func, JSON, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ENUM, UUID, JSONB
from sqlalchemy.orm import relationship

from scout.utils.storage.postgres_database import Base
from scout.utils.storage.postgres_models_llm import LLMModel

project_users = Table(
    "project_users",
    Base.metadata,
    Column("project_id", ForeignKey("project.id"), primary_key=True),
    Column("user_id", ForeignKey("user.id"), primary_key=True),
)

result_chunks = Table(
    "result_chunks",
    Base.metadata,
    Column("chunk_id", ForeignKey("chunk.id"), primary_key=True),
    Column("result_id", ForeignKey("result.id"), primary_key=True),
)

project_criterions = Table(
    "project_criterions",
    Base.metadata,
    Column("project_id", ForeignKey("project.id"), primary_key=True),
    Column("criterion_id", ForeignKey("criterion.id"), primary_key=True),
)


class Rating(Base):
    __tablename__ = "rating"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    positive_rating = Column(Boolean, nullable=False)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())

    project_id = Column(UUID, ForeignKey("project.id"))
    project = relationship("Project", back_populates="ratings")

    user_id = Column(UUID, ForeignKey("user.id"))
    user = relationship("User", back_populates="ratings")

    result_id = Column(UUID, ForeignKey("result.id"))
    result = relationship("Result", back_populates="ratings")


class RoleEnum(enum.Enum):
    ADMIN = "ADMIN"
    UPLOADER = "UPLOADER"
    USER = "USER"


class Role(Base):
    __tablename__ = "role"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    name = Column(ENUM(RoleEnum, name="role_enum", create_type=False), nullable=False)
    description = Column(Text, nullable=True)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_datetime = Column(DateTime(timezone=True), nullable=True)

    users = relationship("User", back_populates="role")


class User(Base):
    __tablename__ = "user"

    email = Column(String, unique=True, nullable=False)
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now(), nullable=True)
    updated_datetime = Column(DateTime(timezone=True), nullable=True)

    role_id = Column(UUID(as_uuid=True), ForeignKey("role.id"))
    role = relationship("Role", back_populates="users")

    projects = relationship("Project", secondary="project_users", back_populates="users")

    ratings = relationship("Rating", back_populates="user")

    audit_logs = relationship("AuditLog", back_populates="user", cascade="all, delete-orphan")

    chat_sessions = relationship("ChatSession", back_populates="user")


class CriterionGate(enum.Enum):
    GATE_0 = "GATE_0"
    GATE_1 = "GATE_1"
    GATE_2 = "GATE_2"
    GATE_3 = "GATE_3"
    GATE_4 = "GATE_4"
    GATE_5 = "GATE_5"
    IPA_GUIDANCE = "IPA_GUIDANCE"
    CUSTOM = "CUSTOM"

    def convert_from_pydantic(value):
        if value == "GATE_0":
            return CriterionGate.GATE_0
        if value == "GATE_1":
            return CriterionGate.GATE_1
        if value == "GATE_2":
            return CriterionGate.GATE_2
        if value == "GATE_3":
            return CriterionGate.GATE_3
        if value == "GATE_4":
            return CriterionGate.GATE_4
        if value == "GATE_5":
            return CriterionGate.GATE_5
        if value == "IPA_GUIDANCE":
            return CriterionGate.IPA_GUIDANCE
        if value == "CUSTOM":
            return CriterionGate.CUSTOM
        return None


class Criterion(Base):
    __tablename__ = "criterion"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    category = Column(String, nullable=False)
    question = Column(String, nullable=False)
    evidence = Column(String, nullable=False)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())

    gate = Column(
        "criterion_gate",
        ENUM(CriterionGate, name="criterion_gate_enum", create_type=False),
        nullable=True,
    )

    results = relationship("Result", back_populates="criterion")

    projects = relationship("Project", secondary="project_criterions", back_populates="criterions")


class Result(Base):
    __tablename__ = "result"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    answer = Column(String, nullable=False)
    full_text = Column(String, nullable=False)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())

    project_id = Column(UUID, ForeignKey("project.id"))
    project = relationship("Project", back_populates="results")

    criterion_id = Column(UUID, ForeignKey("criterion.id"))
    criterion = relationship("Criterion", back_populates="results")

    chunks = relationship("Chunk", secondary="result_chunks", back_populates="results")

    ratings = relationship("Rating", back_populates="result")


class File(Base):
    __tablename__ = "file"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    type = Column(String, nullable=False)
    name = Column(String, nullable=False)
    clean_name = Column(String, nullable=True, default="")
    summary = Column(String, nullable=True, default="")
    source = Column(String, nullable=True, default="")
    published_date = Column(String, nullable=True, default="")
    s3_bucket = Column(String, nullable=True, default="")
    s3_key = Column(String, nullable=True, default="")
    storage_kind = Column(String, nullable=True, default="local")
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())
    # TODO add back in file hash to avoid double uploads, do it the way redbox does

    project_id = Column(UUID, ForeignKey("project.id"))
    project = relationship("Project", back_populates="files")

    chunks = relationship("Chunk", back_populates="file")


class Chunk(Base):
    __tablename__ = "chunk"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    idx = Column(Integer, nullable=False)
    text = Column(String, nullable=False)
    page_num = Column(Integer, nullable=False)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())

    file_id = Column(UUID, ForeignKey("file.id"))
    file = relationship("File", back_populates="chunks")

    results = relationship("Result", secondary="result_chunks", back_populates="chunks")


class Project(Base):
    __tablename__ = "project"

    name = Column(String, nullable=False)
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    results_summary = Column(String, nullable=True, default="")
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())
    knowledgebase_id = Column(String, nullable=True)

    files = relationship("File", back_populates="project")
    criterions = relationship("Criterion", secondary="project_criterions", back_populates="projects")
    results = relationship("Result", back_populates="project")
    users = relationship("User", secondary="project_users", back_populates="projects")
    ratings = relationship("Rating", back_populates="project")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    user_id = Column(UUID, ForeignKey("user.id"))
    action_type = Column(String, nullable=False)  # e.g., 'llm_query', 'file_upload', 'file_delete'
    details = Column(JSONB, nullable=True)  # Store additional context as JSONB
    ip_address = Column(String, nullable=True)
    user_agent = Column(String, nullable=True)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    chat_session_id = Column(UUID, ForeignKey("chat_session.id"))
    chat_session = relationship("ChatSession", back_populates="audit_logs")


class ChatSession(Base):
    __tablename__ = "chat_session"
    
    id = Column(UUID(as_uuid=True), default=uuid.uuid4, primary_key=True)
    created_datetime = Column(DateTime(timezone=True), server_default=func.now())
    updated_datetime = Column(DateTime(timezone=True), onupdate=func.now())
    title = Column(String, nullable=False)
    user_id = Column(UUID, ForeignKey("user.id"))
    project_id = Column(UUID(as_uuid=True), ForeignKey("project.id"), nullable=False)
    deleted = Column(Boolean, default=False, nullable=False)
    
    # Relationships
    project = relationship("Project")
    user = relationship("User", back_populates="chat_sessions")
    audit_logs = relationship("AuditLog", back_populates="chat_session")
