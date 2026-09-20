from sqlalchemy import String , Integer , DateTime , func
from sqlalchemy.orm import Mapped , mapped_column
from app.database import Base
from datetime import datetime

class Report(Base):
    #creation of the table 
    __tablename__ = "reports"

    #the contents of the table ->  column_name : Mapped[datatype] = mapped_column(constraint/datatype)
    id : Mapped[int] = mapped_column(primary_key=True , index=True)
    title : Mapped[str] = mapped_column(String(100))
    description : Mapped[str] = mapped_column(String(500))
    location : Mapped[str] = mapped_column(String(200))

class ReportEvent(Base):
    __tablename__ = "report_events"

    id: Mapped[int] = mapped_column(primary_key=True)
    report_id: Mapped[int] = mapped_column(unique=True, index=True)
    title: Mapped[str] = mapped_column(String(100))
    location: Mapped[str] = mapped_column(String(200))
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )