from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends , HTTPException , Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import Base, engine, SessionLocal
from app import models  , schemas # must be imported so Report registers with Base

#runs once at startup: creates any missing tables
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield

app = FastAPI(lifespan=lifespan)

#one session per request, always closed afterwards
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/reports", response_model=schemas.ReportResponse , status_code=201)
def create_report(report_in:schemas.ReportCreate , db: Session = Depends(get_db)):
    report = models.Report(**report_in.model_dump())
    db.add(report)
    db.commit()
    db.refresh(report)
    return report

@app.get("/reports", response_model=list[schemas.ReportResponse])
def list_reports(
    skip : int = Query(0,ge=0),
    limit : int = Query(100 , ge=1 , le=100),
    db: Session = Depends(get_db)
):
    stmt = select(models.Report).order_by(models.Report.id).offset(skip).limit(limit)
    return db.scalars(stmt).all()


@app.get("/reports/{report_id}",response_model=schemas.ReportResponse)
def get_report(report_id : int , db:Session = Depends(get_db)):
    report = db.get(models.Report , report_id)
    if report is None:
        raise HTTPException(status_code=404, detail= "Report not found")
    return report


@app.patch("/reports/{report_id}", response_model=schemas.ReportResponse)
def update_report(
    report_id : int ,
    report_in : schemas.ReportUpdate,
    db: Session = Depends(get_db)
):
    report = db.get(models.Report , report_id)
    if report is None:
        raise HTTPException(status_code=404 , detail="Report not found")
    
    for field , value in report_in.model_dump(exclude_none=True).items():
        setattr(report , field , value)

    db.commit()
    db.refresh(report)
    return report



@app.delete("/reports/{report_id}" , status_code=204)
def delete_report(report_id:int , db: Session = Depends(get_db)):
    report = db.get(models.Report, report_id)
    if report is None:
        raise HTTPException(status_code=404 , detail="Report not found")
    
    db.delete(report)
    db.commit()