"""
Support tickets (authenticated users)
"""
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models.support_ticket import SupportTicket
from app.models.user import User
from app.schemas.support import SupportTicketCreate, SupportTicketOut

router = APIRouter()


@router.post("/tickets", response_model=SupportTicketOut)
async def create_support_ticket(
    payload: SupportTicketCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Create a support ticket for the current user."""
    ticket = SupportTicket(
        id=uuid.uuid4(),
        user_id=current_user.id,
        subject=payload.subject,
        body=payload.body,
        status="open",
    )
    db.add(ticket)
    db.commit()
    db.refresh(ticket)
    return ticket


@router.get("/tickets")
async def list_my_support_tickets(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(
        None,
        pattern="^(open|in_progress|resolved|closed)$",
        description="Filter by ticket status",
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List support tickets created by the current user (paginated)."""
    q = db.query(SupportTicket).filter(SupportTicket.user_id == current_user.id)
    if status:
        q = q.filter(SupportTicket.status == status)

    total = q.count()
    rows = (
        q.order_by(desc(SupportTicket.created_at))
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {
        "total": total,
        "skip": skip,
        "limit": limit,
        "tickets": [SupportTicketOut.model_validate(r).model_dump() for r in rows],
    }
