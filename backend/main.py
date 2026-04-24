"""Muslin FastAPI application entry point."""

from fastapi import FastAPI

from routes.dev import router as dev_router
from routes.measurements import router as measurements_router
from routes.patterns import router as patterns_router

app = FastAPI(
    title="Muslin API",
    description="Backend for Muslin — sewing pattern adjustment via AI.",
    version="0.1.0",
)

# DEV-ONLY: Register the dev router. In a production deployment this router
# should be conditionally excluded (e.g. behind an ENV flag). It is included
# unconditionally here to keep the scaffold simple during early development.
app.include_router(dev_router)
app.include_router(measurements_router)
app.include_router(patterns_router)
