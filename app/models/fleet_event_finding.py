import uuid
from datetime import datetime

from sqlalchemy import (
    DateTime,
    Float,
    ForeignKey,
    Index,
    String,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class FleetEventFinding(Base):
    """Represent an operational finding produced by a fleet event rule."""

    __tablename__ = "fleet_event_findings"

    __table_args__ = (
        UniqueConstraint(
            "fleet_event_id",
            "rule_id",
            name="uq_fleet_event_findings_event_rule",
        ),
        Index("ix_fleet_event_findings_severity", "severity"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    fleet_event_id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("fleet_events.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )

    rule_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    severity: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    observed_value: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    threshold: Mapped[float] = mapped_column(
        Float,
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
    )

    message: Mapped[str] = mapped_column(
        String(1000),
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )
