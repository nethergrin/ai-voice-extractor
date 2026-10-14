from sqlalchemy.orm import Session
from app.database.models import Session as SessionModel
from datetime import datetime
import secrets


class SessionService:
    @staticmethod
    def create_session(db: Session, client_id: str, mode: str) -> SessionModel:
        session_id = f"{client_id}_{secrets.token_hex(8)}"
        db_session = SessionModel(
            id=session_id,
            client_id=client_id,
            mode=mode,
            status="active"
        )
        db.add(db_session)
        db.commit()
        db.refresh(db_session)
        return db_session

    @staticmethod
    def get_session(db: Session, session_id: str) -> SessionModel:
        return db.query(SessionModel).filter(SessionModel.id == session_id).first()

    @staticmethod
    def get_sessions_by_client(db: Session, client_id: str) -> list[SessionModel]:
        return db.query(SessionModel).filter(SessionModel.client_id == client_id).order_by(SessionModel.created_at.desc()).all()

    @staticmethod
    def close_session(db: Session, session_id: str) -> SessionModel:
        db_session = db.query(SessionModel).filter(SessionModel.id == session_id).first()
        if db_session:
            db_session.status = "closed"
            db_session.closed_at = datetime.utcnow()
            db.commit()
            db.refresh(db_session)
        return db_session

    @staticmethod
    def get_all_sessions(db: Session) -> list[SessionModel]:
        return db.query(SessionModel).order_by(SessionModel.created_at.desc()).all()
