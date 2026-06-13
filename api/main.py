"""
Turkey Logistics DSS — FastAPI Backend
Run: uvicorn api.main:app --reload --port 8000
Docs: http://localhost:8000/docs
"""

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.optimize  import router as optimize_router
from api.routes.analytics import router as analytics_router
from data import SCENARIOS
from api.schemas import ScenarioInfo

app = FastAPI(
    title="Turkey Logistics DSS API",
    description="REST API for the transportation problem optimizer.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(optimize_router)
app.include_router(analytics_router)


@app.get("/", tags=["Health"])
def root():
    return {"status": "ok", "service": "Turkey Logistics DSS API v1.0.0"}


@app.get("/health", tags=["Health"])
def health():
    return {"status": "healthy"}


@app.get("/scenarios", response_model=list[ScenarioInfo], tags=["Data"])
def list_scenarios():
    return [
        ScenarioInfo(
            name=name,
            description=s["description"],
            fuel_multiplier=s["fuel_multiplier"],
        )
        for name, s in SCENARIOS.items()
    ]
