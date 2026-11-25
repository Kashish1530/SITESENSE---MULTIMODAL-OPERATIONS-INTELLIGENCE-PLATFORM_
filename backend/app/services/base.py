from typing import Any, Generic, List, Optional, Type, TypeVar
from sqlalchemy.orm import Session
from app.models.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseService(Generic[ModelType]):
    """Generic Base Service that encapsulates database operations.
    Enforces the rule: Never write database queries directly inside API route handlers.
    """

    def __init__(self, model: Type[ModelType]):
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """Fetch a single record by primary key."""
        return db.query(self.model).filter(self.model.id == id).first()

    def get_multi(
        self, db: Session, *, offset: int = 0, limit: int = 50
    ) -> List[ModelType]:
        """Fetch multiple records with pagination."""
        return db.query(self.model).offset(offset).limit(limit).all()

    def count(self, db: Session) -> int:
        """Count total records in the table."""
        return db.query(self.model).count()
