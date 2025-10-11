from fastapi import FastAPI
from app.api import auth, company
from app.db.session import Base, engine

Base.metadata.create_all(bind=engine)

app = FastAPI(title="TenderBridge API")
app.include_router(auth.router)
app.include_router(company.router)

@app.get("/")
def root():
    return {"message": "Welcome to TenderBridge API"}

