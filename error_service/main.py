from fastapi import FastAPI, Depends, HTTPException  
from sqlalchemy.orm import Session
from sqlalchemy import func
import json

from .db import Base, engine, get_db
from .models import ErrorRecord, User, Service, NotificationRule
from .schemas import ErrorIn, ErrorOut, ServiceIn, ServiceOut, UserIn, UserOut, RuleIn, RuleOut, RuleUserOut

from io import BytesIO
from fastapi.responses import Response
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from datetime import datetime
from fastapi.middleware.cors import CORSMiddleware

from io import BytesIO
from datetime import datetime

# ReportLab graphics (charts)
from reportlab.graphics.shapes import Drawing, String
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics import renderPDF


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Error Logging Service MVP")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:4200"],  # Angular dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

SEVERITY_RANK = {
    "INFO": 10,
    "WARN": 20,
    "ERROR": 30,
    "CRITICAL": 40,
}

def _sev_rank(sev: str | None) -> int:
    return SEVERITY_RANK.get((sev or "ERROR").strip().upper(), 30)


def send_email(user_id: int, service_name: str, severity: str, message: str, error_id: int):
    print(f"[ACTION] EMAIL -> user_id={user_id} service='{service_name}' severity={severity} error_id={error_id} msg='{message}'")


def create_halo_ticket(user_id: int, service_name: str, severity: str, message: str, error_id: int):
    print(f"[ACTION] HALO TICKET -> user_id={user_id} service='{service_name}' severity={severity} error_id={error_id} msg='{message}'")


def send_text_or_call(user_id: int, service_name: str, severity: str, message: str, error_id: int):
    print(f"[ACTION] CALL/TEXT -> user_id={user_id} service='{service_name}' severity={severity} error_id={error_id} msg='{message}'")


def handle_error(machine_name: str, severity: str, message: str, error_id: int, db: Session):
    """
    MVP rule evaluation:
    - Resolve Service by name (case-insensitive)
    - Find all enabled notification rules tied to that service
    - For each rule: if rule.min_severity <= error.severity => perform actions
    """

    machine_norm = (machine_name or "").strip()
    sev_norm = (severity or "ERROR").strip().upper()

    # Resolve service (case-insensitive match)
    service = (
        db.query(Service)
        .filter(func.upper(Service.name) == machine_norm.upper())
        .first()
    )

    if not service:
        print(f"[RULES] No service found for machine='{machine_norm}'. Stored error_id={error_id}, no actions.")
        return

    # Load all enabled rules for this service
    rules = (
        db.query(NotificationRule)
        .filter(
            NotificationRule.service_id == service.id,
            NotificationRule.enabled == True,  # noqa: E712
        )
        .all()
    )

    if not rules:
        print(f"[RULES] No rules for service='{service.name}'. Stored error_id={error_id}, no actions.")
        return

    err_rank = _sev_rank(sev_norm)

    for rule in rules:
        rule_rank = _sev_rank(rule.min_severity)

        # Minimum severity check
        if err_rank < rule_rank:
            continue

        # Action bits -> call stub functions
        if rule.do_email:
            send_email(rule.user_id, service.name, sev_norm, message, error_id)

        if rule.do_halo_ticket:
            create_halo_ticket(rule.user_id, service.name, sev_norm, message, error_id)

        if rule.do_call:
            send_text_or_call(rule.user_id, service.name, sev_norm, message, error_id)


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

    # evaluate rules + run actions (MVP prints)
    handle_error(
        machine_name=rec.machine,
        severity=rec.severity,
        message=rec.message,
        error_id=rec.id,
        db=db,
    )

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

@app.get("/services", response_model=list[ServiceOut])
def list_services(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(Service)
        .order_by(Service.group.asc(), Service.name.asc())
        .limit(limit)
        .all()
    )
    return [ServiceOut(id=r.id, created_at=r.created_at, name=r.name, group=r.group) for r in rows]


@app.post("/services", response_model=ServiceOut, status_code=201)
def create_service(payload: ServiceIn, db: Session = Depends(get_db)):
    name = payload.name.strip()
    group = payload.group.strip()

    existing = (
        db.query(Service)
        .filter(Service.name == name, Service.group == group)
        .first()
    )
    if existing:
        return ServiceOut(
            id=existing.id,
            created_at=existing.created_at,
            name=existing.name,
            group=existing.group,
        )

    rec = Service(name=name, group=group)
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return ServiceOut(id=rec.id, created_at=rec.created_at, name=rec.name, group=rec.group)

@app.get("/users", response_model=list[UserOut])
def list_users(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(User)
        .order_by(User.id.desc())
        .limit(limit)
        .all()
    )
    return [
        UserOut(
            id=r.id,
            created_at=r.created_at,
            first_name=r.first_name,
            last_name=r.last_name,
            role=r.role,
            email=r.email,
            phone_number=r.phone_number,
        )
        for r in rows
    ]


@app.post("/users", response_model=UserOut, status_code=201)
def create_user(payload: UserIn, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()

    existing = db.query(User).filter(User.email == email).first()
    if existing:
        # idempotent: return existing instead of 409
        return UserOut(
            id=existing.id,
            created_at=existing.created_at,
            first_name=existing.first_name,
            last_name=existing.last_name,
            role=existing.role,
            email=existing.email,
            phone_number=existing.phone_number,
        )

    rec = User(
        first_name=payload.first_name.strip(),
        last_name=payload.last_name.strip(),
        role=payload.role.strip(),
        email=email,
        phone_number=(payload.phone_number.strip() if payload.phone_number else None),
    )
    db.add(rec)
    db.commit()
    db.refresh(rec)

    return UserOut(
        id=rec.id,
        created_at=rec.created_at,
        first_name=rec.first_name,
        last_name=rec.last_name,
        role=rec.role,
        email=rec.email,
        phone_number=rec.phone_number,
    )

@app.get("/rules", response_model=list[RuleOut])
def list_rules(limit: int = 200, db: Session = Depends(get_db)):
    rows = (
        db.query(NotificationRule)
        .order_by(NotificationRule.id.desc())
        .limit(limit)
        .all()
    )
    return [
        RuleOut(
            id=r.id,
            created_at=r.created_at,
            user_id=r.user_id,
            service_id=r.service_id,
            min_severity=r.min_severity,
            enabled=r.enabled,
            do_email=r.do_email,
            do_call=r.do_call,
            do_halo_ticket=r.do_halo_ticket,
        )
        for r in rows
    ]

@app.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    rule = db.query(NotificationRule).filter(NotificationRule.id == rule_id).first()
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")

    db.delete(rule)
    db.commit()
    return


@app.post("/rules", response_model=RuleOut, status_code=201)
def create_rule(payload: RuleIn, db: Session = Depends(get_db)):

    # ---- Resolve or create user ----
    user = None

    if payload.user_id is not None:
        user = db.query(User).filter(User.id == payload.user_id).first()

        # If user_id was provided but doesn't exist, allow auto-create if payload.user exists
        if not user and payload.user:
            email = payload.user.email.strip().lower()
            user = db.query(User).filter(User.email == email).first()

            if not user:
                user = User(
                    first_name=payload.user.first_name.strip(),
                    last_name=payload.user.last_name.strip(),
                    role=payload.user.role.strip(),
                    email=email,
                    phone_number=(payload.user.phone_number.strip() if payload.user.phone_number else None),
                )
                db.add(user)
                db.commit()
                db.refresh(user)

        if not user:
            raise HTTPException(status_code=400, detail="Unknown user_id (and no user payload provided to auto-create).")

    else:
        # No user_id -> must provide user object
        if not payload.user:
            raise HTTPException(status_code=400, detail="Provide either user_id or user.")

        email = payload.user.email.strip().lower()
        user = db.query(User).filter(User.email == email).first()

        if not user:
            user = User(
                first_name=payload.user.first_name.strip(),
                last_name=payload.user.last_name.strip(),
                role=payload.user.role.strip(),
                email=email,
                phone_number=(payload.user.phone_number.strip() if payload.user.phone_number else None),
            )
            db.add(user)
            db.commit()
            db.refresh(user)

    # ---- Validate service exists ----
    service = db.query(Service).filter(Service.id == payload.service_id).first()
    if not service:
        raise HTTPException(status_code=400, detail="Unknown service_id")

    # ---- Upsert rule by (user_id, service_id) ----
    existing = (
        db.query(NotificationRule)
        .filter(
            NotificationRule.user_id == user.id,
            NotificationRule.service_id == payload.service_id,
        )
        .first()
    )

    if existing:
        existing.min_severity = payload.min_severity
        existing.enabled = payload.enabled
        existing.do_email = payload.do_email
        existing.do_call = payload.do_call
        existing.do_halo_ticket = payload.do_halo_ticket
        db.commit()
        db.refresh(existing)
        r = existing
    else:
        r = NotificationRule(
            user_id=user.id,
            service_id=payload.service_id,
            min_severity=payload.min_severity,
            enabled=payload.enabled,
            do_email=payload.do_email,
            do_call=payload.do_call,
            do_halo_ticket=payload.do_halo_ticket,
        )
        db.add(r)
        db.commit()
        db.refresh(r)

    return RuleOut(
        id=r.id,
        created_at=r.created_at,
        user_id=r.user_id,
        service_id=r.service_id,
        min_severity=r.min_severity,
        enabled=r.enabled,
        do_email=r.do_email,
        do_call=r.do_call,
        do_halo_ticket=r.do_halo_ticket,
    )

@app.get("/rules/by-machine", response_model=list[RuleUserOut])
def rules_by_machine(machine: str, db: Session = Depends(get_db)):
    machine_norm = machine.strip()

    service = (
        db.query(Service)
        .filter(func.upper(Service.name) == machine_norm.upper())
        .first()
    )
    if not service:
        return []

    rows = (
        db.query(NotificationRule, User)
        .join(User, User.id == NotificationRule.user_id)
        .filter(
            NotificationRule.service_id == service.id,
            NotificationRule.enabled == True,  # noqa: E712
        )
        .order_by(User.last_name.asc(), User.first_name.asc())
        .all()
    )

    return [
        RuleUserOut(
            user_id=u.id,
            first_name=u.first_name,
            last_name=u.last_name,
            email=u.email,
            phone_number=u.phone_number,

            rule_id=r.id,
            enabled=r.enabled,
            min_severity=r.min_severity,
            do_email=r.do_email,
            do_call=r.do_call,
            do_halo_ticket=r.do_halo_ticket,
        )
        for (r, u) in rows
    ]


@app.get("/report/health.pdf")
def health_report_pdf(db: Session = Depends(get_db)):
    # Example metric: last 10 errors
    rows = (
        db.query(ErrorRecord)
        .order_by(ErrorRecord.id.desc())
        .limit(10)
        .all()
    )

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4

    y = height - 50
    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, y, "System Health Report")
    y -= 25

    c.setFont("Helvetica", 10)
    c.drawString(50, y, f"Generated: {datetime.now().isoformat(timespec='seconds')}")
    y -= 30

    # =========================
    # 1) PIE CHART (mock data)
    # =========================
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Severity distribution")
    y -= 10

    # Mock data (swap for real aggregation later)
    severity_labels = ["Info", "Warning", "Error", "Critical"]
    severity_values = [12, 7, 5, 2]

    pie = Pie()
    pie.x = 0
    pie.y = 0
    pie.width = 220
    pie.height = 220
    pie.data = severity_values
    pie.labels = severity_labels
    pie.sideLabels = 1
    pie.slices.strokeWidth = 0.5

    pie_drawing = Drawing(320, 240)
    pie_drawing.add(pie)
    pie_drawing.add(String(0, 225, "Example chart", fontSize=8))

    # Render drawing onto the PDF canvas (x, y are bottom-left of the drawing)
    pie_x = 50
    pie_y = y - 240  # reserve 240pt of height
    renderPDF.draw(pie_drawing, c, pie_x, pie_y)
    y = pie_y - 20

    # =========================
    # 2) BAR CHART (mock data)
    # =========================
    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Errors per machine")
    y -= 10

    machines = ["IMA-01", "CEFLA-02", "AGV-07", "BOX-01", "PALL-03"]
    machine_counts = [4, 2, 6, 1, 3]

    bar = VerticalBarChart()
    bar.x = 40
    bar.y = 30
    bar.height = 180
    bar.width = 380
    bar.data = [machine_counts]  # list-of-series
    bar.categoryAxis.categoryNames = machines
    bar.valueAxis.valueMin = 0
    bar.valueAxis.valueMax = max(machine_counts) + 2
    bar.valueAxis.valueStep = 1
    bar.barWidth = 18
    bar.groupSpacing = 10

    bar_drawing = Drawing(480, 240)
    bar_drawing.add(bar)

    bar_x = 50
    bar_y = y - 240
    # If you’re near bottom, new page
    if bar_y < 50:
        c.showPage()
        y = height - 50
        bar_y = y - 240

    renderPDF.draw(bar_drawing, c, bar_x, bar_y)
    y = bar_y - 30

    # =========================
    # 3) TABLE-ish LIST (your existing section)
    # =========================
    if y < 120:
        c.showPage()
        y = height - 50

    c.setFont("Helvetica-Bold", 12)
    c.drawString(50, y, "Latest errors")
    y -= 20

    c.setFont("Helvetica", 10)
    for r in rows:
        line = f"#{r.id}  {r.created_at}  {r.machine}  {r.severity}  {r.message}"
        c.drawString(50, y, line[:120])  # simple truncation
        y -= 14
        if y < 50:
            c.showPage()
            y = height - 50
            c.setFont("Helvetica", 10)

    c.save()
    pdf_bytes = buf.getvalue()
    buf.close()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=system_health_report.pdf"},
    )

@app.delete("/errors", status_code=204)
def delete_all_errors(db: Session = Depends(get_db)):
    db.query(ErrorRecord).delete()
    db.commit()
    return



