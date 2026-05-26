import os
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base, async_session_maker
from app.config.settings import settings
from app.routes.ticket_routes import router as ticket_router
from app.services.bloom_service import bloom_service

logger = logging.getLogger("main")
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Create database tables if they do not exist
    logger.info("Initializing database tables...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables initialized.")

    # 2. Startup: Load tickets and initialize Bloom Filter
    async with async_session_maker() as session:
        await bloom_service.initialize_from_db(session)
        
    yield
    # 3. Shutdown: Dispose database engine connections
    logger.info("Shutting down engine...")
    await engine.dispose()

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A production-ready Ticket Management System optimized with a Bloom Filter search cache.",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for external development or API testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routes under /api
app.include_router(ticket_router, prefix="/api")

# Serve the static UI home page at the root route "/"
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def serve_index():
    index_path = os.path.join(os.path.dirname(__file__), "static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    return HTMLResponse(content="<h1>Ticket CRM Frontend Not Found</h1><p>Please ensure app/static/index.html exists.</p>", status_code=404)

# Mount static files (CSS, JS) for web interface
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir, exist_ok=True)
    os.makedirs(os.path.join(static_dir, "css"), exist_ok=True)
    os.makedirs(os.path.join(static_dir, "js"), exist_ok=True)

app.mount("/static", StaticFiles(directory=static_dir), name="static")
