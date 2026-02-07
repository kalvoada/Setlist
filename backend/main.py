from fastapi import FastAPI
from src.database.database import engine, Base
from src.routers import users, posts

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI()

# Include the routers
app.include_router(users.router)
app.include_router(posts.router)

@app.get("/")
def root():
    return {"message": "Welcome to the API"}