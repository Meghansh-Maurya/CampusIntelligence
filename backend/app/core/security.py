from __future__ import annotations

import json
import logging
import os

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.models import User

logger = logging.getLogger(__name__)


def _upsert_user(db: Session, uid: str, email: str | None, name: str | None = None) -> User:
    user = db.scalar(select(User).where(User.firebase_uid == uid))
    if user is None:
        user = User(firebase_uid=uid, email=email, full_name=name)
        db.add(user)
        try:
            db.commit()
        except IntegrityError:
            # Two first requests for the same identity can race to insert the row.
            # Roll back the losing transaction and load the row created by the winner.
            db.rollback()
            user = db.scalar(select(User).where(User.firebase_uid == uid))
            if user is None:
                raise
    else:
        if email:
            user.email = email
        if name and not user.full_name:
            user.full_name = name
        db.commit()
    db.refresh(user)
    return user


def _firebase_app():
    try:
        import firebase_admin
        from firebase_admin import credentials
    except ImportError as exc:
        raise HTTPException(status_code=500, detail="Install backend dependencies from requirements.txt to enable Firebase authentication.") from exc
    try:
        return firebase_admin.get_app()
    except ValueError:
        pass

    try:
        if settings.firebase_service_account_json and settings.firebase_service_account_json.get_secret_value().strip():
            service_account = json.loads(settings.firebase_service_account_json.get_secret_value())
            credential = credentials.Certificate(service_account)
        elif os.getenv("GOOGLE_APPLICATION_CREDENTIALS"):
            credential = credentials.Certificate(os.environ["GOOGLE_APPLICATION_CREDENTIALS"])
        else:
            credential = credentials.ApplicationDefault()

        options = {"projectId": settings.firebase_project_id} if settings.firebase_project_id else None
        return firebase_admin.initialize_app(credential, options=options)
    except Exception as exc:
        logger.exception("Firebase Admin could not initialize")
        raise HTTPException(
            status_code=503,
            detail="Firebase authentication is not configured. Set FIREBASE_PROJECT_ID and credentials before using AUTH_MODE=firebase.",
        ) from exc


def get_current_user(
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
    x_dev_user_id: str | None = Header(default=None),
    x_dev_email: str | None = Header(default=None),
) -> User:
    """Resolve the current user. Development header auth is blocked when DEBUG=false."""
    if settings.auth_mode == "development":
        if not settings.debug:
            raise HTTPException(status_code=500, detail="Development authentication is disabled when DEBUG=false.")
        uid = (x_dev_user_id or "demo-student").strip()
        if not uid or len(uid) > 128:
            raise HTTPException(status_code=400, detail="X-Dev-User-Id must contain 1-128 characters.")
        email = (x_dev_email or f"{uid}@example.local").strip()
        return _upsert_user(db, uid, email)

    if settings.auth_mode != "firebase":
        raise HTTPException(status_code=500, detail="Unsupported authentication mode.")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="A Firebase ID token is required in the Authorization: Bearer header.")

    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise HTTPException(status_code=401, detail="The bearer token is empty.")
    try:
        from firebase_admin import auth as firebase_auth
        decoded = firebase_auth.verify_id_token(token, app=_firebase_app(), check_revoked=True)
    except HTTPException:
        raise
    except Exception as exc:
        logger.info("Firebase token verification failed")
        raise HTTPException(status_code=401, detail="The Firebase ID token is invalid or expired.") from exc

    uid = str(decoded.get("uid", ""))
    if not uid:
        raise HTTPException(status_code=401, detail="The verified token did not contain a user ID.")
    return _upsert_user(db, uid, decoded.get("email"), decoded.get("name"))
