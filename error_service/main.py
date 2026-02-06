from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
import json

from .db import Base, engine, get_db
from .models import ErrorRecord
from .schemas import ErrorIn, ErrorOut

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Error Logging Service MVP")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/errors", response_model=ErrorOut, status_code=201)
def create_error(payload: ErrorIn, db: Session = Depends(get_db)):
    rec = ErrorRecord(
        machine=payload.machine.strip().upper(),
        message=payload.message.strip(),
        severity=(payload.severity or "ERROR"),
        raw_payload=json.dumps(payload.model_dump(mode="json"), ensure_ascii=False),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return ErrorOut(
        id=rec.id,
        created_at=rec.created_at,
        machine=rec.machine,
        message=rec.message,
        severity=rec.severity,
    )

@app.get("/errors", response_model=list[ErrorOut])
def list_errors(limit: int = 50, db: Session = Depends(get_db)):
    rows = (
        db.query(ErrorRecord)
        .order_by(ErrorRecord.id.desc())
        .limit(limit)
        .all()
    )
    return [
        ErrorOut(
            id=r.id,
            created_at=r.created_at,
            machine=r.machine,
            message=r.message,
            severity=r.severity,
        )
        for r in rows
    ]
