from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app import crud, schemas, models
from app.database import SessionLocal, engine

models.Base.metadata.create_all(bind=engine)

identify_router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@identify_router.post("/identify", response_model=schemas.ContactResponse)
def identify_contact(payload: schemas.ContactRequest, db: Session = Depends(get_db)):
    return crud.identify(payload, db)