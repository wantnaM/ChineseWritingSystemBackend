"""
FastAPI 应用启动入口
运行: uvicorn main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import api_router
from app.api.auth_routes import auth_router
from app.api.teacher_routes import teacher_router
from app.core.config import settings

app = FastAPI(
    title="语文一体化写作系统 API",
    description="Schema-Driven 教学平台后端接口",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(api_router)
app.include_router(auth_router, prefix="/api/v1")
app.include_router(teacher_router, prefix="/api/v1")


@app.get("/health")
async def health():
    return {"status": "ok"}
