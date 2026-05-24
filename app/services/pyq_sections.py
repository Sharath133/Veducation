import uuid

from sqlalchemy.orm import Session

from app.config import settings
from app.models.pyq import PYQCategory, PYQSection, PYQSectionPDF


DEFAULT_PYQ_STRUCTURE = [
    {
        "code": "upsc",
        "title": "UPSC",
        "icon": "account_balance",
        "sections": ["Prelims", "Mains", "Interview"],
    },
    {
        "code": "state_pscs",
        "title": "STATE PSCs",
        "icon": "location_city",
        "sections": ["APPSC", "TSPSC", "Other State PSCs"],
    },
    {
        "code": "central_exams",
        "title": "Other central exams",
        "icon": "public",
        "sections": ["SSC", "Banking", "Railways", "Defence"],
    },
]


def ensure_default_pyq_structure(db: Session) -> None:
    if db.query(PYQCategory).count() > 0:
        return

    for category_index, category_data in enumerate(DEFAULT_PYQ_STRUCTURE):
        category = PYQCategory(
            id=uuid.uuid4(),
            code=category_data["code"],
            title=category_data["title"],
            icon=category_data["icon"],
            display_order=category_index,
        )
        db.add(category)
        db.flush()

        for section_index, section_title in enumerate(category_data["sections"]):
            db.add(
                PYQSection(
                    id=uuid.uuid4(),
                    category_id=category.id,
                    title=section_title,
                    display_order=section_index,
                )
            )

    db.commit()


def serialize_pyq_structure(db: Session, include_inactive: bool = False) -> list[dict]:
    ensure_default_pyq_structure(db)

    category_query = db.query(PYQCategory)
    if not include_inactive:
        category_query = category_query.filter(PYQCategory.is_active.is_(True))

    categories = category_query.order_by(
        PYQCategory.display_order,
        PYQCategory.title,
    ).all()

    output = []
    for category in categories:
        section_query = db.query(PYQSection).filter(
            PYQSection.category_id == category.id,
        )
        if not include_inactive:
            section_query = section_query.filter(PYQSection.is_active.is_(True))

        sections = section_query.order_by(
            PYQSection.display_order,
            PYQSection.title,
        ).all()

        output.append(
            {
                "id": str(category.id),
                "code": category.code,
                "title": category.title,
                "icon": category.icon,
                "display_order": category.display_order,
                "is_active": category.is_active,
                "sections": [
                    _serialize_section(db, section, include_inactive)
                    for section in sections
                ],
            }
        )

    return output


def _serialize_section(
    db: Session,
    section: PYQSection,
    include_inactive: bool,
) -> dict:
    pdf_query = db.query(PYQSectionPDF).filter(
        PYQSectionPDF.section_id == section.id,
    )
    if not include_inactive:
        pdf_query = pdf_query.filter(PYQSectionPDF.is_active.is_(True))

    pdfs = pdf_query.order_by(
        PYQSectionPDF.display_order,
        PYQSectionPDF.created_at,
    ).all()

    return {
        "id": str(section.id),
        "category_id": str(section.category_id),
        "title": section.title,
        "display_order": section.display_order,
        "is_active": section.is_active,
        "pdfs": [
            {
                "id": str(pdf.id),
                "title": pdf.title,
                "file_path": pdf.file_path,
                "url": f"/{pdf.file_path}",
                "display_order": pdf.display_order,
                "is_active": pdf.is_active,
            }
            for pdf in pdfs
        ],
    }


def next_pdf_order(db: Session, section_id) -> int:
    return db.query(PYQSectionPDF).filter(
        PYQSectionPDF.section_id == section_id,
    ).count()


def pyq_upload_relative_path(*parts: str) -> str:
    return "/".join([settings.UPLOAD_DIR, "pyq-sections", *parts])
