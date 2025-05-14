from datetime import datetime
from enum import Enum
from typing import List, Optional
from uuid import UUID

import tiktoken
from pydantic import BaseModel, ConfigDict, Extra, Field, constr, field_validator
from pydantic_core.core_schema import ValidationInfo

"""
Maintain all schemas in this one file, splitting out into multiple files
causes circular and reference dependency issues that pydantic masks
"""


encoding = tiktoken.get_encoding("cl100k_base")

global_model_config = ConfigDict(
    from_attributes=True,  # Use ORM to retrieve objects
    extra=Extra.ignore,  # Ignore any extra values that get passed in when serializing
    use_enum_values=True,  # Use enum values rather than raw enum
)


class RatingBase(BaseModel):
    model_config = global_model_config

    id: UUID
    positive_rating: bool
    created_datetime: datetime
    updated_datetime: Optional[datetime]


class RatingCreate(BaseModel):
    positive_rating: bool
    user: "UserBase"
    project: "ProjectBase"
    result: "ResultBase"


class RatingUpdate(RatingCreate):
    id: UUID


class RatingFilter(BaseModel):
    positive_rating: Optional[bool] = None
    user: Optional["UserBase"] = None
    project: Optional["ProjectBase"] = None
    result: Optional["ResultBase"] = None

class Rating(RatingBase):
    user: "UserBase"
    project: "ProjectBase"
    result: "ResultBase"


class ChunkBase(BaseModel):
    # Allows pydantic/sqlalchemy to use ORM to pull out related objects instead of just references to them
    model_config = global_model_config

    id: UUID
    idx: int
    text: str
    page_num: int
    created_datetime: datetime
    updated_datetime: Optional[datetime]


class ChunkCreate(BaseModel):
    idx: int
    text: str
    page_num: int
    file: Optional["FileBase"] = None
    results: Optional[list["ResultBase"]] = Field(default_factory=list)


class ChunkUpdate(ChunkCreate):
    id: UUID


class ChunkFilter(BaseModel):
    idx: Optional[int] = None
    text: Optional[str] = None
    page_num: Optional[int] = None
    file: Optional["FileBase"] = None
    results: Optional[list["ResultBase"]] = []


class Chunk(ChunkBase):
    # Pydantic objects are sometimes coerced. Added strict = true.
    file: Optional["FileBase"] = Field(None, strict=True)
    results: Optional[list["ResultBase"]] = Field(default_factory=list)


class CriterionGate(str, Enum):
    GATE_0 = "GATE_0"
    GATE_1 = "GATE_1"
    GATE_2 = "GATE_2"
    GATE_3 = "GATE_3"
    GATE_4 = "GATE_4"
    GATE_5 = "GATE_5"
    IPA_GUIDANCE = "IPA_GUIDANCE"
    CUSTOM = "CUSTOM"


class CriterionBase(BaseModel):
    # Allows pydantic/sqlalchemy to use ORM to pull out related objects instead of just references to them
    model_config = global_model_config
    id: UUID
    created_datetime: datetime
    updated_datetime: Optional[datetime]
    gate: CriterionGate
    category: str
    question: str
    evidence: str


class CriterionCreate(BaseModel):
    gate: CriterionGate
    category: str
    question: str
    evidence: str
    projects: Optional[list["ProjectBase"]] = Field(default_factory=list)
    results: Optional[list["ResultBase"]] = Field(default_factory=list)

    @field_validator("projects")
    @classmethod
    def validate_project_name(cls, v: str | None, info: ValidationInfo):
        # TODO: What gate value do we want to check here
        if info.data.get("gate") == CriterionGate.CUSTOM and not v:
            raise ValueError("project is required when category is Custom")
        return v


class CriterionUpdate(CriterionCreate):
    id: UUID


class CriterionFilter(BaseModel):
    gate: Optional[CriterionGate] = None
    category: Optional[str] = None
    question: Optional[str] = None
    evidence: Optional[str] = None
    projects: Optional[list["ProjectBase"]] = []
    results: Optional[list["ResultBase"]] = []


class Criterion(CriterionBase):
    projects: Optional[list["ProjectBase"]] = Field(default_factory=list)
    results: Optional[list["ResultBase"]] = Field(default_factory=list)


class FileBase(BaseModel):
    # Allows pydantic/sqlalchemy to use ORM to pull out related objects instead of just references to them
    model_config = global_model_config

    id: UUID
    created_datetime: datetime
    updated_datetime: Optional[datetime]
    type: str
    name: str
    clean_name: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    published_date: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None  # This is the key of the file in s3.
    storage_kind: str = "local"
    url: Optional[str] = None
    # TODO add back in file hash to avoid double uploads, do it the way redbox does


class FileCreate(BaseModel):
    type: str
    name: str
    clean_name: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    published_date: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    storage_kind: str = "local"
    project_id: Optional[UUID] = None
    chunks: Optional[list["ChunkBase"]] = Field(default_factory=list)


class FileUpdate(FileCreate):
    id: UUID


class FileFilter(BaseModel):
    type: Optional[str] = None
    name: Optional[str] = None
    clean_name: Optional[str] = None
    summary: Optional[str] = None
    source: Optional[str] = None
    published_date: Optional[str] = None
    s3_bucket: Optional[str] = None
    s3_key: Optional[str] = None
    storage_kind: Optional[str] = []
    project: Optional["ProjectBase"] = None
    chunks: Optional[list["ChunkBase"]] = []


class File(FileBase):
    project: Optional["ProjectBase"] = None
    chunks: Optional[list["ChunkBase"]] = Field(default_factory=list)


class ProjectBase(BaseModel):
    # Allows pydantic/sqlalchemy to use ORM to pull out related objects instead of just references to them
    model_config = global_model_config

    id: UUID
    created_datetime: datetime
    updated_datetime: Optional[datetime]
    name: str
    results_summary: Optional[str] = None
    knowledgebase_id: Optional[str] = None


class ProjectCreate(BaseModel):
    name: str
    results_summary: Optional[str] = None
    users: Optional[List["UserBase"]] = Field(default_factory=list)
    files: Optional[List["FileBase"]] = Field(default_factory=list)
    criterions: Optional[List["CriterionBase"]] = Field(default_factory=list)
    results: Optional[List["ResultBase"]] = Field(default_factory=list)
    knowledgebase_id: Optional[str] = None


class ProjectUpdate(ProjectCreate):
    id: UUID
    knowledgebase_id: Optional[str] = None


class ProjectFilter(BaseModel):
    name: Optional[str] = None
    results_summary: Optional[str] = None
    users: Optional[List["UserBase"]] = []
    files: Optional[List["FileBase"]] = []
    criterions: Optional[List["CriterionBase"]] = []
    results: Optional[List["ResultBase"]] = []


class Project(ProjectBase):
    users: Optional[List["UserBase"]] = Field(default_factory=list)
    files: Optional[List["FileBase"]] = Field(default_factory=list)
    criterions: Optional[List["CriterionBase"]] = Field(default_factory=list)
    results: Optional[List["ResultBase"]] = Field(default_factory=list)
    ratings: Optional[List["RatingBase"]] = Field(default_factory=list)


class ResultBase(BaseModel):
    # Allows pydantic/sqlalchemy to use ORM to pull out related objects instead of just references to them
    model_config = global_model_config

    id: UUID
    created_datetime: datetime
    updated_datetime: Optional[datetime]
    answer: str
    full_text: str


class ResultCreate(BaseModel):
    answer: str
    full_text: str
    criterion: Optional[UUID] = None  # Change to UUID
    project: Optional[UUID] = None    # Change to UUID 
    chunks: Optional[list[UUID]] = Field(default_factory=list)  # Change to list of UUIDs


class ResultUpdate(ResultCreate):
    id: UUID


class ResultFilter(BaseModel):
    answer: Optional[str] = None
    full_text: Optional[str] = None
    criterion: Optional[UUID] = None  # Change to UUID
    project: Optional[UUID] = None    # Change to UUID
    chunks: Optional[list[UUID]] = [] # Change to list of UUIDs


class Result(ResultBase):
    criterion: Optional["CriterionBase"] = None
    project: Optional["ProjectBase"] = None
    chunks: Optional[list["ChunkBase"]] = Field(default_factory=list)
    ratings: Optional[list["RatingBase"]] = Field(default_factory=list)


class RoleEnum(str, Enum):
    ADMIN = "ADMIN"
    UPLOADER = "UPLOADER"
    USER = "USER"

class RoleBase(BaseModel):
    model_config = global_model_config
    
    id: UUID
    name: RoleEnum
    description: Optional[str] = None
    created_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None

class RoleCreate(BaseModel):
    name: RoleEnum
    description: Optional[str] = None

class RoleUpdate(RoleCreate):
    id: UUID
    updated_datetime: datetime = Field(default_factory=datetime.utcnow)
    
class Role(RoleBase):
    pass
class RoleFilter(BaseModel):
    name: Optional[RoleEnum] = None
    description: Optional[str] = None
    created_datetime: Optional[datetime] = None
    updated_datetime: Optional[datetime] = None

    class Config:
        use_enum_values = True
class UserBase(BaseModel):
    model_config = global_model_config

    id: UUID
    email: str
    created_datetime: datetime
    updated_datetime: Optional[datetime] = None
    role_id: Optional[UUID] = None

class UserCreate(BaseModel):
    email: str
    role_id: Optional[UUID] = None

class UserUpdate(BaseModel):
    id: UUID
    email: str
    role_id: Optional[UUID] = None
    updated_datetime: datetime = Field(default_factory=datetime.utcnow)

class UserFilter(BaseModel):
    email: Optional[str] = None
    projects: Optional[List["ProjectBase"]] = []
    role_id: Optional[UUID] = None

class User(UserBase):
    projects: List["ProjectBase"] = Field(default_factory=list)
    ratings: List["RatingBase"] = Field(default_factory=list)
    role: Optional[Role] = None


class SourceEnum(str, Enum):
    IPA = "IPA"
    PROJECT = "project"
    DEPARTMENT = "department"
    OTHER = "other"


class FileInfo(BaseModel):
    clean_name: str = Field(None, description="A user-friendly name for the file")
    summary: constr(max_length=500) = Field(  # type:ignore
        None,
        description="A brief summary of the file content, limited to 500 characters",
    )
    source: SourceEnum = Field(
        None,
        description="The origin of the file: IPA, project, department, or other",
    )
    published_date: str = Field(
        None,
        description="The date when the file was published or last updated in DD-MM-YYYY format",
    )


class AuditLogBase(BaseModel):
    model_config = global_model_config

    id: UUID
    timestamp: datetime
    user_id: UUID
    action_type: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None


class AuditLogCreate(BaseModel):
    user_id: UUID
    action_type: str
    details: Optional[dict] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    chat_session_id: Optional[UUID] = None


class AuditLog(AuditLogBase):
    user: Optional[UserBase] = None
    
class ChatSessionBase(BaseModel):
    # Allows pydantic/sqlalchemy to use ORM to pull out related objects instead of just references to them
    model_config = global_model_config
    
    id: UUID
    created_datetime: datetime
    updated_datetime: Optional[datetime]
    title: str
    

class ChatSessionCreate(BaseModel):
    title: str

    
class ChatSession(ChatSessionBase):
    user: Optional[UserBase] = None
    audit_logs: Optional[List[AuditLogBase]] = Field(default_factory=list)

class ChatSessionUpdate(BaseModel):
    id: UUID
    title: Optional[str] = None
    updated_datetime: Optional[datetime] = None
