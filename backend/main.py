import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router as api_router
from utils.browser import BrowserManager
from utils.logging_setup import setup_logging
from dotenv import load_dotenv

load_dotenv()
setup_logging()

app = FastAPI(
    title="JobPulse API",
    description="UK Vacancy Demand Verification Tool Backend Service",
    version="1.0.0"
)

# Set up CORS
origins = [
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {
        "status": "online",
        "service": "JobPulse UK Vacancy DVM Tool API",
        "demo_mode": os.getenv("DEMO_MODE", "true").lower() == "true"
    }

@app.on_event("startup")
async def startup_event():
    # Warm up browser in production/live mode
    demo_mode = os.getenv("DEMO_MODE", "true").lower() == "true"
    if not demo_mode:
        try:
            await BrowserManager.get_browser()
            print("Playwright Browser launched successfully.")
        except Exception as e:
            print(f"Error launching Playwright Browser: {e}")

@app.on_event("shutdown")
async def shutdown_event():
    await BrowserManager.close_browser()
    print("Playwright Browser closed.")
