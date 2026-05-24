"""PYQs (Previous Year Questions) Endpoints"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.pyq_sections import serialize_pyq_structure

router = APIRouter()


@router.get("/sections")
async def get_pyq_sections(db: Session = Depends(get_db)):
    """Get student-facing PYQ categories, sections, and PDFs."""
    return {"categories": serialize_pyq_structure(db)}


@router.get("/list")
async def get_pyqs_list():
    """Get PYQs list"""
    return {
        "pyqs": [
            {
                "id": "pyq-2024-01",
                "title": "2024 January Test Paper",
                "date": "2024-01-15",
                "total_questions": 20,
                "subject": "General Knowledge",
                "difficulty": "Medium"
            },
            {
                "id": "pyq-2024-02",
                "title": "2024 February Test Paper",
                "date": "2024-02-15",
                "total_questions": 20,
                "subject": "Mathematics",
                "difficulty": "Hard"
            },
            {
                "id": "pyq-2024-03",
                "title": "2024 March Test Paper",
                "date": "2024-03-15",
                "total_questions": 20,
                "subject": "Science",
                "difficulty": "Easy"
            },
        ]
    }


@router.get("/{pyq_id}")
async def get_pyq(pyq_id: str):
    """Get specific PYQ"""
    return {
        "id": pyq_id,
        "title": f"PYQ {pyq_id}",
        "questions": [
            {
                "id": "q1",
                "question_text": "Sample question 1",
                "options": ["A", "B", "C", "D"],
                "correct_answer": "A"
            }
        ]
    }

