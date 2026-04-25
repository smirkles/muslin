"""Muslin FastAPI application entry point."""

import os

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routes.body import router as body_router
from routes.cascades import router as cascades_router
from routes.dev import router as dev_router
from routes.measurements import router as measurements_router
from routes.patterns import router as patterns_router
from routes.photos import router as photos_router

load_dotenv(".env.local")

app = FastAPI(
    title="Muslin API",
    description="Backend for Muslin — sewing pattern adjustment via AI.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[os.environ.get("CORS_ORIGIN", "http://localhost:3000")],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register the dev router only when APP_ENV is not "production".
# include_in_schema=False keeps /dev/* out of /docs and /openapi.json in all envs.
if os.environ.get("APP_ENV") != "production":
    app.include_router(dev_router, include_in_schema=False)
app.include_router(measurements_router)
app.include_router(patterns_router)
app.include_router(photos_router)
app.include_router(cascades_router)
app.include_router(body_router)
