from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models import Document, User
from app.schemas import ProfileUpdate, UserRead

router = APIRouter()


@router.get("/me", response_model=UserRead)
def read_my_profile(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.patch("/me", response_model=UserRead)
def update_my_profile(
    payload: ProfileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> User:
    updates = payload.model_dump(exclude_unset=True)
    for field in {"skills", "interests", "career_goals"}:
        if field in updates and updates[field] is None:
            raise HTTPException(status_code=422, detail=f"{field} must be a list; use an empty list to clear it.")
    for field, value in updates.items():
        setattr(current_user, field, value)
    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT, response_class=Response)
def delete_my_account(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    documents = db.scalars(select(Document).where(Document.user_id == current_user.id)).all()
    for document in documents:
        file_path = settings.storage_dir / document.stored_filename
        try:
            if file_path.exists():
                file_path.unlink()
        except OSError:
            # Database deletion should still proceed; orphaned files can be cleaned up separately.
            pass
    db.delete(current_user)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
