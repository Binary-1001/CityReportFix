from sqlalchemy import String , Integer
from sqlalchemy.orm import Mapped , mapped_column
from app.database import Base

class Report(Base):
    #creation of the table 
    __tablename__ = "reports"

    #the contents of the table ->  column_name : Mapped[datatype] = mapped_column(constraint/datatype)
    id : Mapped[int] = mapped_column(primary_key=True , index=True)
    title : Mapped[str] = mapped_column(String(100))
    description : Mapped[str] = mapped_column(String(500))
    location : Mapped[str] = mapped_column(String(200))