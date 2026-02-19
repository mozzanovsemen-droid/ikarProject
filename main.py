from fastapi import FastAPI
from routers import auth, reports, admin
from database import init_db

app = FastAPI(title="Система отчётов студентов v2.0")


init_db()

# Подключаем роутеры
app.include_router(auth.router, tags=["Аутентификация"])
app.include_router(reports.router, prefix="/api", tags=["Отчёты"])
app.include_router(admin.router, prefix="/admin", tags=["Админ"])

@app.get("/")
def root():
    return {"message": "Система отчётов студентов ✅", "version": "2.0"}

@app.get("/health")
def health_check():
    return {"status": "healthy"}
