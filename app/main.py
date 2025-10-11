from fastapi import FastAPI
from app.api import auth
from app.db.session import Base, engine

# create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(title="TenderBridge API")
app.include_router(auth.router)

@app.get("/")
def root():
    return {"message": "Welcome to TenderBridge API"}
