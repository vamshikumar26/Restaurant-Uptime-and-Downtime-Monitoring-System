from fastapi import FastAPI
from routes import endpoints

#creating instance for FastAPI
app = FastAPI()

app.include_router(endpoints.router)