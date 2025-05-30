from datetime import datetime
import logging
from uuid import UUID
from typing import Generator

from decorator import contextmanager
from sqlalchemy import or_
from sqlalchemy.orm import Session
from sqlalchemy import select, insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.dialects.postgresql import insert as pg_insert

from scout.DataIngest.models.schemas import AuditLogCreate, Chunk as PyChunk
from scout.DataIngest.models.schemas import ChunkCreate
from scout.DataIngest.models.schemas import ChunkFilter
from scout.DataIngest.models.schemas import ChunkUpdate
from scout.DataIngest.models.schemas import Criterion as PyCriterion
from scout.DataIngest.models.schemas import CriterionCreate
from scout.DataIngest.models.schemas import CriterionFilter
from scout.DataIngest.models.schemas import CriterionUpdate
from scout.DataIngest.models.schemas import File as PyFile
from scout.DataIngest.models.schemas import FileCreate
from scout.DataIngest.models.schemas import FileFilter
from scout.DataIngest.models.schemas import FileUpdate
from scout.DataIngest.models.schemas import Project as PyProject
from scout.DataIngest.models.schemas import ProjectCreate
from scout.DataIngest.models.schemas import ProjectFilter
from scout.DataIngest.models.schemas import ProjectUpdate
from scout.DataIngest.models.schemas import Rating as PyRating
from scout.DataIngest.models.schemas import RatingCreate
from scout.DataIngest.models.schemas import RatingFilter
from scout.DataIngest.models.schemas import RatingUpdate
from scout.DataIngest.models.schemas import Result as PyResult
from scout.DataIngest.models.schemas import ResultCreate
from scout.DataIngest.models.schemas import ResultFilter
from scout.DataIngest.models.schemas import ResultUpdate
from scout.DataIngest.models.schemas import User as PyUser
from scout.DataIngest.models.schemas import UserBase
from scout.DataIngest.models.schemas import UserCreate
from scout.DataIngest.models.schemas import UserFilter
from scout.DataIngest.models.schemas import UserUpdate
from scout.DataIngest.models.schemas import AuditLog as PyAuditLog
from scout.DataIngest.models.schemas import RoleFilter
from scout.DataIngest.models.schemas import Role as PyRole
from scout.DataIngest.models.schemas import RoleEnum
from scout.utils.storage.filesystem import S3StorageHandler
from scout.utils.storage.postgres_database import SessionLocal
from scout.utils.storage.postgres_models import Chunk as SqChunk
from scout.utils.storage.postgres_models import Criterion as SqCriterion
from scout.utils.storage.postgres_models import CriterionGate
from scout.utils.storage.postgres_models import File as SqFile
from scout.utils.storage.postgres_models import Project as SqProject
from scout.utils.storage.postgres_models import project_criterions
from scout.utils.storage.postgres_models import project_users
from scout.utils.storage.postgres_models import Rating as SqRating
from scout.utils.storage.postgres_models import Result as SqResult
from scout.utils.storage.postgres_models import result_chunks
from scout.utils.storage.postgres_models import User as SqUser
from scout.utils.storage.postgres_models import AuditLog as SqAuditLog
from scout.utils.storage.postgres_models import Role as SqRole
# Pydantic models
# SqlAlchemy models

# Pydantic models
# SqlAlchemy models

pydantic_model_to_sqlalchemy_model_map = {
    PyCriterion: SqCriterion,
    PyChunk: SqChunk,
    PyFile: SqFile,
    PyProject: SqProject,
    PyResult: SqResult,
    PyUser: SqUser,
    CriterionCreate: SqCriterion,
    ChunkCreate: SqChunk,
    FileCreate: SqFile,
    ProjectCreate: SqProject,
    ResultCreate: SqResult,
    UserCreate: SqUser,
    CriterionUpdate: SqCriterion,
    ChunkUpdate: SqChunk,
    FileUpdate: SqFile,
    ProjectUpdate: SqProject,
    ResultUpdate: SqResult,
    UserUpdate: SqUser,
    PyRating: SqRating,
    RatingCreate: SqRating,
    RatingUpdate: SqRating,
    PyAuditLog: SqAuditLog,
    PyRole: SqRole,
}

pydantic_update_model_to_base_model = {
    CriterionUpdate: PyCriterion,
    ChunkUpdate: PyChunk,
    FileUpdate: PyFile,
    ProjectUpdate: PyProject,
    ResultUpdate: PyResult,
    UserUpdate: PyUser,
    RatingUpdate: PyRating,
}

pydantic_update_model_to_sqlalchemy_model = {
    CriterionUpdate: SqCriterion,
    ChunkUpdate: SqChunk,
    FileUpdate: SqFile,
    ProjectUpdate: SqProject,
    ResultUpdate: SqResult,
    UserUpdate: SqUser,
    RatingUpdate: SqRating,
}

pydantic_create_model_to_base_model = {
    CriterionCreate: PyCriterion,
    ChunkCreate: PyChunk,
    FileCreate: PyFile,
    ProjectCreate: PyProject,
    ResultCreate: PyResult,
    UserCreate: PyUser,
    RatingCreate: PyRating,
}

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@contextmanager
def SessionManager() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    except:
        # if we fail somehow rollback the connection
        logger.debug("Db operation failed... rolling back")
        db.rollback()
        raise
    finally:
        db.close()


def get_all(
    model: PyCriterion | PyChunk | PyFile | PyProject | PyResult | PyUser | PyRating | PyAuditLog,
) -> list[PyCriterion | PyChunk | PyFile | PyProject | PyResult | PyUser | PyRating | PyAuditLog] | None:
    with SessionManager() as db:
        try:
            sq_model = pydantic_model_to_sqlalchemy_model_map.get(model)
            result = db.query(sq_model).all()
            results = []
            for item in result:
                parsed_item = model.model_validate(item)
                if model is PyFile and parsed_item.s3_key:
                    parsed_item.url = str(S3StorageHandler().get_pre_signed_url(parsed_item.s3_key, parsed_item.s3_bucket))
                results.append(parsed_item)  # Parse retrieved info into pydantic model and add to list
            return results
        except Exception as _:
            logger.exception(f"Failed to get all items, {model}")


def get_by_id(
    model: PyCriterion | PyChunk | PyFile | PyProject | PyResult | PyUser | PyRating | PyRole,
    object_id: UUID,
) -> PyCriterion | PyChunk | PyFile | PyProject | PyResult | PyUser | PyRole | None:
    with SessionManager() as db:
        try:
            sq_model = pydantic_model_to_sqlalchemy_model_map.get(model)
            result = db.query(sq_model).filter_by(id=object_id).one_or_none()
            if result is None:
                return None
            parsed_item = model.model_validate(result)
            if model is PyFile and parsed_item.s3_key:
                parsed_item.url = str(S3StorageHandler().get_pre_signed_url(parsed_item.s3_key, parsed_item.s3_bucket))
            return parsed_item
        except Exception as _:
            logger.exception(f"Failed to get item by id, {model}, {object_id}")


def get_or_create_item(
    model: CriterionCreate | ChunkCreate | FileCreate | ProjectCreate | ResultCreate | UserCreate | RatingCreate | AuditLogCreate,
) -> PyProject | PyResult | PyUser | PyChunk | PyFile | PyCriterion | PyRating | PyAuditLog:
    model_type = type(model)
    with SessionManager() as db:
        try:
            if model_type is ProjectCreate:
                return _get_or_create_project(model, db)
            if model_type is UserCreate:
                return _get_or_create_user(model, db)
            if model_type is CriterionCreate:
                return _get_or_create_criterion(model, db)
            if model_type is ResultCreate:
                return _get_or_create_result(model, db)
            if model_type is ChunkCreate:
                return _get_or_create_chunk(model, db)
            if model_type is FileCreate:
                return _get_or_create_file(model, db)
            if model_type is RatingCreate:
                return _get_or_create_rating(model, db)
            if model_type is AuditLogCreate:
                return _get_or_create_auditlog(model, db)
        except Exception as _:
            logger.exception(f"Failed to get or create item, {model}")


def _get_or_create_rating(model: RatingCreate, db: Session) -> PyRating:
    sq_model = SqRating
    existing_item = (
        db.query(sq_model)
        .filter(
            sq_model.project_id == model.project.id,
            sq_model.user_id == model.user.id,
            sq_model.result_id == model.result.id,
        )
        .first()
    )
    if existing_item:
        return PyRating.model_validate(existing_item)
    item_to_add = sq_model(
        positive_rating=model.positive_rating,
        project_id=model.project.id,
        user_id=model.user.id,
        result_id=model.result.id,
    )
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it

    db.flush()
    return PyRating.model_validate(item_to_add)


def _get_or_create_project(
    model: ProjectCreate,
    db: Session,
) -> PyProject:
    sq_model = SqProject
    existing_item = db.query(sq_model).filter_by(name=model.name).first()
    if existing_item:
        return PyProject.model_validate(existing_item)
    item_to_add = sq_model(
        name=model.name,
        results_summary=model.results_summary,
        knowledgebase_id=model.knowledgebase_id
    )
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it

    for file in model.files:
        existing_file: SqFile | None = db.query(SqFile).get(file.id)
        existing_file.project = item_to_add
        db.commit()

    for criterion in model.criterions:
        existing_criterion: SqCriterion | None = db.query(SqCriterion).get(criterion.id)
        db.execute(project_criterions.insert().values(criterion_id=existing_criterion.id, project_id=item_to_add.id))
        db.commit()

    for result in model.results:
        existing_result: SqResult | None = db.query(SqResult).get(result.id)
        existing_result.project = item_to_add
        db.commit()

    for user in model.users:
        existing_user: SqUser | None = db.query(SqUser).get(user.id)
        db.execute(project_users.insert().values(user_id=existing_user.id, project_id=item_to_add.id))
        db.commit()

    db.flush()

    py_base_model = pydantic_create_model_to_base_model.get(type(model))
    return py_base_model.model_validate(item_to_add)


def _get_or_create_user(
    model: UserCreate,
    db: Session,
) -> PyUser:
    sq_model = SqUser
    existing_item = db.query(sq_model).filter_by(email=model.email).first()
    if existing_item:
        return PyUser.model_validate(existing_item)
    item_to_add = sq_model(email=model.email)
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it

    return PyUser.model_validate(item_to_add)


def _get_or_create_criterion(
    model: CriterionCreate,
    db: Session,
) -> PyCriterion:
    sq_model = SqCriterion
    existing_item = (
        db.query(sq_model).filter_by(category=model.category, question=model.question, evidence=model.evidence).first()
    )
    if existing_item:
        return PyCriterion.model_validate(existing_item)
    item_to_add = sq_model(
        gate=model.gate.value,
        question=model.question,
        evidence=model.evidence,
        category=model.category,
    )
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it

    for result in model.results:
        existing_result: SqResult | None = db.query(SqResult).get(result.id)
        existing_result.criterion = item_to_add
        db.commit()

    for project in model.projects:
        existing_project: SqProject | None = db.query(SqProject).get(project.id)
        db.execute(project_criterions.insert().values(criterion_id=item_to_add.id, project_id=existing_project.id))
        db.commit()

    db.flush()
    return PyCriterion.model_validate(item_to_add)


def _get_or_create_chunk(
    model: ChunkCreate,
    db: Session,
) -> PyChunk:
    sq_model = SqChunk
    existing_item = db.query(sq_model).filter_by(idx=model.idx, text=model.text, page_num=model.page_num).first()
    if existing_item:
        return PyChunk.model_validate(existing_item)
    assert model.file.id is not None, f"File id from {model.model_dump()} is None"
    logger.info(f"File id from {model.model_dump()} is {model.file.id}")
    # time.sleep(60)
    item_to_add = sq_model(
        idx=model.idx,
        text=model.text,
        page_num=model.page_num,
        file_id=model.file.id,
    )
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it

    for result in model.results:
        existing_result: SqResult | None = db.query(SqResult).get(result.id)
        db.execute(result_chunks.insert().values(chunk_id=item_to_add.id, result_id=existing_result.id))
        db.commit()

    db.flush()
    return PyChunk.model_validate(item_to_add)


def _get_or_create_file(
    model: FileCreate,
    db: Session,
) -> PyFile:
    sq_model = SqFile
    existing_item = db.query(sq_model).filter_by(type=model.type, name=model.name).first()
    if existing_item:
        parsed_item = PyFile.model_validate(existing_item)
        if parsed_item.s3_key:
            parsed_item.url = str(S3StorageHandler().get_pre_signed_url(parsed_item.s3_key, parsed_item.s3_bucket))
        return parsed_item

    item_to_add = sq_model(
        type=model.type,
        name=model.name,
        clean_name=model.clean_name,
        summary=model.summary,
        source=model.source,
        published_date=model.published_date,
        s3_bucket=model.s3_bucket,
        s3_key=model.s3_key,
        storage_kind=model.storage_kind,
        project_id=model.project_id,
    )
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it

    for chunk in model.chunks:
        existing_chunk: SqChunk | None = db.query(SqChunk).get(chunk.id)
        existing_chunk.file_id = item_to_add.id
        db.commit()

    db.flush()
    parsed_item = PyFile.model_validate(item_to_add)
    if parsed_item.s3_key:
        parsed_item.url = str(S3StorageHandler().get_pre_signed_url(parsed_item.s3_key, parsed_item.s3_bucket))
    return parsed_item


def _get_or_create_result(
    model: ResultCreate,
    db: Session,
) -> PyResult:
    sq_model = SqResult
    existing_item = db.query(sq_model).filter_by(answer=model.answer, full_text=model.full_text).first()
    if existing_item:
        return PyResult.model_validate(existing_item)
    
    item_to_add = sq_model(
        answer=model.answer,
        full_text=model.full_text,
        project_id=model.project,  # Now using UUID directly
        criterion_id=model.criterion,  # Now using UUID directly
    )
    db.add(item_to_add)
    db.commit()
    db.flush()  # Refresh created item to add ID to it
    
    for chunk_id in model.chunks:  # Now iterating over UUIDs
        existing_chunk: SqChunk | None = db.query(SqChunk).get(chunk_id)
        if not existing_chunk:
            continue
            
        # Check if the entry already exists before inserting
        existing_result_chunk = db.execute(
            select(result_chunks).where(
                result_chunks.c.chunk_id == existing_chunk.id,
                result_chunks.c.result_id == item_to_add.id
            )
        ).scalar_one_or_none()
        
        if existing_result_chunk is None:
            try:
                db.execute(
                    insert(result_chunks).values(
                        chunk_id=existing_chunk.id,
                        result_id=item_to_add.id
                    )
                )
                db.commit()
            except IntegrityError as e:
                db.rollback()
                logger.error("IntegrityError during insertion: %s", e)
                # Ignore only if the error is due to a duplicate key violation
                if "duplicate key value violates unique constraint" not in str(e):
                    raise
        else:
            logger.debug("result_chunks already exists, not adding")
    
    db.flush()
    return PyResult.model_validate(item_to_add)


def _get_or_create_auditlog(model: AuditLogCreate, db: Session):
    """Create a new audit log entry. Audit logs are always created, never retrieved."""
    from scout.utils.storage.postgres_models import AuditLog as SqAuditLog
    
    # Convert datetime objects in details to ISO format strings
    if model.details:
        details = {}
        for key, value in model.details.items():
            if isinstance(value, datetime):
                details[key] = value.isoformat()
            else:
                details[key] = value
    else:
        details = None
    
    item_to_add = SqAuditLog(
        user_id=model.user_id,
        action_type=model.action_type,
        details=details,
        ip_address=model.ip_address,
        user_agent=model.user_agent,
        chat_session_id=model.chat_session_id
    )
    
    try:
        db.add(item_to_add)
        db.commit()
        db.flush()  # Refresh created item to add ID to it
        
        from scout.DataIngest.models.schemas import AuditLog
        return AuditLog.model_validate(item_to_add)
    except Exception as e:
        logger.error(f"Failed to create audit log: {e}")
        db.rollback()
        raise


def get_all_audit_logs() -> list[PyAuditLog]:
    """Retrieve all rows from the audit log table."""
    with SessionManager() as db:
        try:
            sq_model = SqAuditLog
            result = db.query(sq_model).all()
            return [PyAuditLog.model_validate(item) for item in result]
        except Exception as e:
            logger.exception("Failed to retrieve audit logs")
            raise


def delete_item(
    model: PyCriterion | PyChunk | PyFile | PyProject | PyResult | PyUser | PyRating,
) -> UUID:
    with SessionManager() as db:
        try:
            sq_model = pydantic_model_to_sqlalchemy_model_map.get(type(model))
            item = db.query(sq_model).get(model.id)
            db.delete(item)
            db.commit()
            return model.id
        except Exception as _:
            logger.exception(f"Failed to delete item, {model}")


def update_item(
    model: CriterionUpdate | ChunkUpdate | FileUpdate | ProjectUpdate | ResultUpdate | UserUpdate | RatingUpdate,
) -> PyCriterion | PyChunk | PyFile | PyProject | PyResult | PyUser | PyRating | None:
    model_type = type(model)
    with SessionManager() as db:
        try:
            if model_type is ProjectUpdate:
                return _update_project(model, db)
            if model_type is UserUpdate:
                return _update_user(model, db)
            if model_type is CriterionUpdate:
                return _update_criterion(model, db)
            if model_type is ResultUpdate:
                return _update_result(model, db)
            if model_type is ChunkUpdate:
                return _update_chunk(model, db)
            if model_type is FileUpdate:
                return _update_file(model, db)
            if model_type is RatingUpdate:
                return _update_rating(model, db)
        except Exception as _:
            logger.exception(f"Failed to update item, {model}")


def _update_rating(model, db):
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()

    if item is None:
        return None

    item.positive_rating = model.positive_rating
    item.result_id = model.result.id if model.result else None
    item.project_id = model.project.id if model.project else None
    item.user_id = model.user.id if model.user else None

    db.commit()
    db.flush()  # Refresh updated item

    return PyRating.model_validate(item)


def _update_criterion(model: CriterionUpdate, db: Session) -> PyCriterion | None:
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()

    if item is None:
        return None

    item.category = model.category
    item.question = model.question
    item.evidence = model.evidence
    item.gate = CriterionGate.convert_from_pydantic(model.gate)
    item.results = [db.query(SqResult).get(result.id) for result in model.results]
    item.projects = [db.query(SqProject).get(project.id) for project in model.projects]

    db.commit()
    db.flush()  # Refresh updated item

    return PyCriterion.model_validate(item)


def _update_chunk(model: ChunkUpdate, db: Session) -> PyChunk | None:
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()

    assert model.file.id is not None, f"File id from {model.model_dump()} is None"
    logger.info(f"UPDATED CHUNK: File id from {model.model_dump()} is {model.file.id}")
    if item is None:
        return None

    item.idx = model.idx
    item.text = model.text
    item.page_num = model.page_num
    item.file_id = model.file.id if model.file else None
    item.results = [db.query(SqResult).get(result.id) for result in model.results]

    db.commit()
    db.flush()  # Refresh updated item

    return PyChunk.model_validate(item)


def _update_file(model: FileUpdate, db: Session) -> PyFile | None:
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()
    logger.info(f"UPDATED FILE: File id from {model.model_dump()} is {item.id}")
    if item is None:
        return None

    # Update basic attributes
    item.type = model.type
    item.name = model.name
    item.clean_name = model.clean_name
    item.summary = model.summary
    item.source = model.source
    item.published_date = model.published_date
    item.s3_bucket = model.s3_bucket
    item.s3_key = model.s3_key
    item.storage_kind = model.storage_kind
    item.project_id = model.project.id if model.project else None

    # Don't update chunks relationship unless explicitly provided
    if model.chunks:
        item.chunks = [db.query(SqChunk).get(chunk.id) for chunk in model.chunks]

    db.commit()
    db.flush()  # Refresh updated item

    parsed_item = PyFile.model_validate(item)
    if parsed_item.s3_key:
        parsed_item.url = str(S3StorageHandler().get_pre_signed_url(parsed_item.s3_key, parsed_item.s3_bucket))
    return parsed_item


def _update_project(model: ProjectUpdate, db: Session) -> PyProject | None:
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()

    if item is None:
        return None

    update_data = model.model_dump(exclude_unset=True)

    # Define fields that are lists of related objects and their corresponding SQLAlchemy models
    relation_fields = {
        'files': SqFile,
        'criterions': SqCriterion,
        'results': SqResult,
        'users': SqUser,
    }

    apply_updates(item, update_data, db, relation_fields)

    db.commit()
    db.flush()

    return PyProject.model_validate(item)


def _update_user(model: UserUpdate, db: Session) -> PyUser | None:
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()

    if item is None:
        return None

    update_data = model.model_dump(exclude_unset=True)

    apply_updates(
        item,
        update_data,
        db,
        relation_fields={},  # No many-to-many fields in this example
        extra_fields={"updated_datetime": datetime.utcnow()}
    )

    db.commit()
    db.refresh(item)

    return PyUser.model_validate(item)

def apply_updates(item, update_data: dict, db: Session, relation_fields: dict = {}, extra_fields: dict = {}):
    for field, value in update_data.items():
        if field in relation_fields:
            related_model = relation_fields[field]
            existing_related = getattr(item, field)

            # Convert list of dicts or objects into a set of related items from DB
            incoming_ids = set()
            related_items_to_add = []

            for obj in value:
                obj_id = obj["id"] if isinstance(obj, dict) else getattr(obj, "id", None)
                if obj_id is not None:
                    incoming_ids.add(obj_id)
                    db_item = db.query(related_model).get(obj_id)
                    if db_item and db_item not in existing_related:
                        related_items_to_add.append(db_item)

            # Only add new items, do not remove existing ones
            for db_item in related_items_to_add:
                existing_related.append(db_item)

        else:
            setattr(item, field, value)

    for field, value in extra_fields.items():
        setattr(item, field, value)

        
def _update_result(model: ResultUpdate, db: Session) -> PyResult | None:
    sq_model = pydantic_update_model_to_sqlalchemy_model.get(type(model))
    item = db.query(sq_model).filter(sq_model.id == model.id).one_or_none()

    if item is None:
        return None
    item.answer = model.answer
    item.full_text = model.full_text
    if model.project is not None:
        item.project_id = model.project.id
    item.criterion_id = model.criterion.id if model.criterion else None

    db.commit()
    db.flush()  # Refresh updated item

    return PyResult.model_validate(item)

def filter_items(
    model: UserFilter | ProjectFilter | ResultFilter | ChunkFilter | CriterionFilter | FileFilter | RatingFilter | RoleFilter, current_user: PyUser
) -> list[PyUser | PyProject | PyResult | PyChunk | PyCriterion | PyFile | PyRating | PyRole]:
    model_type = type(model)
    with SessionManager() as db:
        try:
            if model_type is ProjectFilter:
                return _filter_project(model, db, current_user)
            if model_type is UserFilter:
                return _filter_user(model, db)
            if model_type is CriterionFilter:
                return _filter_criterion(model, db)
            if model_type is ResultFilter:
                return _filter_result(model, db, current_user)
            if model_type is ChunkFilter:
                return _filter_chunk(model, db, current_user)
            if model_type is FileFilter:
                return _filter_file(model, db, current_user)
            if model_type is RatingFilter:
                return _filter_rating(model, db, current_user)
            if model_type is RoleFilter:
                return _filter_role(model, db)
        except Exception as e:
            logger.exception(f"Failed to filter items, {model}: {e}")
            return []

def _filter_rating(model, db):
    query = db.query(SqRating)
    if model.positive_rating:
        query = query.filter(SqRating.positive_rating.ilike(f"%{model.positive_rating}%"))
    if model.project:
        query = query.filter(SqRating.project_id == model.project.id)
    if model.result:
        query = query.filter(SqRating.result_id == model.result.id)
    if model.user:
        query = query.filter(SqRating.user_id == model.user.id)

    result = query.all()
    results = []
    for item in result:
        results.append(PyRating.model_validate(item))
    return results

def _filter_role(model: RoleFilter, db: Session) -> list[PyRole]:
    query = db.query(SqRole)
    
    if model.name:
        query = query.filter(SqRole.name == model.name)
    if model.description:
        query = query.filter(SqRole.description.ilike(f"%{model.description}%"))
    if model.created_datetime:
        query = query.filter(SqRole.created_datetime >= model.created_datetime)
    if model.updated_datetime:
        query = query.filter(SqRole.updated_datetime >= model.updated_datetime)

    result = query.all()
    results: list[PyRole] = []
    for item in result:
        results.append(PyRole.model_validate(item))
    return results

def _filter_user(model: UserFilter, db: Session) -> list[PyUser]:
    query = db.query(SqUser)
    if model.email:
        query = query.filter(SqUser.email == model.email)
    if model.projects:
        project_ids = [project.id for project in model.projects]
        query = query.join(project_users, SqUser.id == project_users.c.user_id)
        query = query.filter(or_(project_users.c.project_id.in_(project_ids)))

    result = query.all()
    results = []
    for item in result:
        results.append(PyUser.model_validate(item))
    return results


def _filter_file(model: FileFilter, db: Session, current_user: PyUser) -> list[PyFile]:
    query = db.query(SqFile)
    user_project_ids = [project.id for project in current_user.projects]
    query = query.filter(SqFile.project_id.in_(user_project_ids))

    if model.name:
        query = query.filter(SqFile.name.ilike(f"%{model.name}%"))
    if model.type:
        query = query.filter(SqFile.type.ilike(f"%{model.type}%"))
    if model.clean_name:
        query = query.filter(SqFile.clean_name.ilike(f"%{model.clean_name}%"))
    if model.summary:
        query = query.filter(SqFile.summary.ilike(f"%{model.summary}%"))
    if model.source:
        query = query.filter(SqFile.source.ilike(f"%{model.source}%"))
    if model.project:
        query = query.filter(SqFile.project_id == model.project.id)
    if model.s3_key:
        query = query.filter(SqFile.s3_key == model.s3_key)
    if model.chunks:
        chunk_ids = [chunk.id for chunk in model.chunks]
        query = query.join(SqChunk)
        query = query.filter(or_(SqChunk.id.in_(chunk_ids)))

    result = query.all()
    results = []
    for item in result:
        parsed_item = PyFile.model_validate(item)
        if parsed_item.s3_key:
            parsed_item.url = str(S3StorageHandler().get_pre_signed_url(parsed_item.s3_key, parsed_item.s3_bucket))
        results.append(PyFile.model_validate(parsed_item))
    return results


def _filter_chunk(model: ChunkFilter, db: Session, current_user: PyUser) -> list[PyChunk]:
    query = db.query(SqChunk)
    if model.idx:
        query = query.filter(SqChunk.idx.ilike(f"%{model.idx}%"))
    if model.text:
        query = query.filter(SqChunk.text.ilike(f"%{model.text}%"))
    if model.page_num:
        query = query.filter(SqChunk.page_num == model.page_num)
    if model.file:
        query = query.filter(SqChunk.file_id == model.file.id)
    if model.results:
        result_ids = [result.id for result in model.results]
        query = query.join(result_chunks, SqChunk.id == result_chunks.c.result_id)
        query = query.filter(or_(result_chunks.c.result_id.in_(result_ids)))

    result = query.all()
    results = []
    for item in result:
        results.append(PyChunk.model_validate(item))
    return results


def _filter_criterion(model: CriterionFilter, db: Session) -> list[PyCriterion]:
    query = db.query(SqCriterion)
    if model.category:
        query = query.filter(SqCriterion.gate.ilike(f"%{model.gate}%"))
    if model.gate:
        query = query.filter(SqCriterion.gate == model.gate)
    if model.question:
        query = query.filter(SqCriterion.question.ilike(f"%{model.question}%"))
    if model.evidence:
        query = query.filter(SqCriterion.evidence.ilike(f"%{model.evidence}%"))
    if model.projects:
        project_ids = [project.id for project in model.projects]
        query = query.join(project_criterions, SqCriterion.id == project_criterions.c.criterion_id)
        query = query.filter(or_(project_criterions.c.project_id.in_(project_ids)))
    if model.results:
        result_ids = [result.id for result in model.results]
        query = query.join(SqResult)
        query = query.filter(or_(SqResult.id.in_(result_ids)))

    result = query.all()
    results = []
    for item in result:
        results.append(PyCriterion.model_validate(item))
    return results


def _filter_project(model: ProjectFilter, db: Session, current_user: PyUser) -> list[PyProject]:
    query = db.query(SqProject)
   
    # If the current user is not an admin, filter by projects associated with the user
    if current_user.role.name != RoleEnum.ADMIN:
        user_project_ids = [project.id for project in current_user.projects]
        query = query.filter(SqProject.id.in_(user_project_ids))
        
    if model.name:
        query = query.filter(SqProject.name.ilike(f"%{model.name}%"))
    if model.results_summary:
        query = query.filter(SqProject.results_summary.ilike(f"%{model.results_summary}%"))

    if model.files:
        file_ids = [file.id for file in model.files]
        query = query.join(SqFile)
        query = query.filter(or_(SqFile.id.in_(file_ids)))

    if model.results:
        result_ids = [result.id for result in model.results]
        query = query.join(SqResult)
        query = query.filter(or_(SqResult.id.in_(result_ids)))

    if model.users:
        user_ids = [user.id for user in model.users]
        query = query.join(project_users, SqProject.id == project_users.c.project_id)
        query = query.filter(or_(project_users.c.user_id.in_(user_ids)))

    if model.criterions:
        criterion_ids = [criterion.id for criterion in model.criterions]
        query = query.join(project_criterions, SqProject.id == project_criterions.c.project_id)
        query = query.filter(or_(project_criterions.c.criterion_id.in_(criterion_ids)))

    result = query.all()
    results: list[PyProject] = []
    for item in result:
        results.append(PyProject.model_validate(item))
    return results


def _filter_result(model: ResultFilter, db: Session, current_user: PyUser) -> list[PyResult]:
    query = db.query(SqResult)
    if model.answer:
        query = query.filter(SqResult.answer.ilike(f"%{model.answer}%"))
    if model.full_text:
        query = query.filter(SqResult.full_text.ilike(f"%{model.full_text}%"))
    if model.criterion:
        query = query.filter(SqResult.criterion_id == model.criterion)
    if model.project:
        query = query.filter(SqResult.project_id == model.project)

    if model.chunks:
        query = query.join(result_chunks, SqResult.id == result_chunks.c.result_id)
        query = query.filter(or_(result_chunks.c.chunk_id.in_(model.chunks)))

    # Only filter by user's projects if there is a current_user and they are not admin
    if current_user is not None and current_user.role.name != RoleEnum.ADMIN:
        user_project_ids = [project.id for project in current_user.projects]
        query = query.filter(SqResult.project_id.in_(user_project_ids))

    result = query.all()
    results = []
    for item in result:
        results.append(PyResult.model_validate(item))
    return results
