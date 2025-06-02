from fastapi import FastAPI
from app.routes import identify_router


app = FastAPI()
app.include_router(identify_router)
