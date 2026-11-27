from typing import List, Optional, Tuple
import uuid
from sqlalchemy.orm import Session
from app.core.exceptions import ConflictError, NotFoundError
from app.models.knowledge_compliance import Rule
from app.schemas.rules import RuleCreate, RuleResponse, RuleUpdate


class RuleService:
    """Service encapsulating database queries for Compliance Rules."""

    @classmethod
    def list_rules(
        cls,
        db: Session,
        *,
        limit: int = 50,
        offset: int = 0,
        is_active: Optional[bool] = None,
    ) -> Tuple[List[RuleResponse], int]:
        """List rules with pagination and active filter."""
        query = db.query(Rule)
        if is_active is not None:
            query = query.filter(Rule.is_active == is_active)

        total = query.count()
        rules = query.order_by(Rule.name).offset(offset).limit(limit).all()
        return [RuleResponse.model_validate(r) for r in rules], total

    @classmethod
    def get_rule(cls, db: Session, rule_id: uuid.UUID) -> RuleResponse:
        """Fetch single rule by ID."""
        rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if not rule:
            raise NotFoundError(message=f"Rule '{rule_id}' not found.")
        return RuleResponse.model_validate(rule)

    @classmethod
    def create_rule(cls, db: Session, payload: RuleCreate) -> RuleResponse:
        """Register a new compliance rule (Admin only)."""
        existing = db.query(Rule).filter(Rule.name == payload.name.strip()).first()
        if existing:
            raise ConflictError(message=f"Rule with name '{payload.name}' already exists.")

        rule = Rule(
            name=payload.name.strip(),
            description=payload.description.strip(),
            rule_type=payload.rule_type.strip(),
            parameters=payload.parameters,
            policy_ref=payload.policy_ref.strip(),
            severity=payload.severity or "high",
            is_active=payload.is_active if payload.is_active is not None else True,
            policy_id=payload.policy_id,
        )
        db.add(rule)
        db.commit()
        db.refresh(rule)
        return RuleResponse.model_validate(rule)

    @classmethod
    def update_rule(cls, db: Session, rule_id: uuid.UUID, payload: RuleUpdate) -> RuleResponse:
        """Update existing compliance rule configuration."""
        rule = db.query(Rule).filter(Rule.id == rule_id).first()
        if not rule:
            raise NotFoundError(message=f"Rule '{rule_id}' not found.")

        if payload.name is not None:
            rule.name = payload.name.strip()
        if payload.description is not None:
            rule.description = payload.description.strip()
        if payload.rule_type is not None:
            rule.rule_type = payload.rule_type.strip()
        if payload.parameters is not None:
            rule.parameters = payload.parameters
        if payload.policy_ref is not None:
            rule.policy_ref = payload.policy_ref.strip()
        if payload.severity is not None:
            rule.severity = payload.severity
        if payload.is_active is not None:
            rule.is_active = payload.is_active
        if payload.policy_id is not None:
            rule.policy_id = payload.policy_id

        db.commit()
        db.refresh(rule)
        return RuleResponse.model_validate(rule)
