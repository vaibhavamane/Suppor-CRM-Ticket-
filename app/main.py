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
    # Detect if we are running in the Vercel serverless environment
    is_vercel = os.environ.get("VERCEL") == "1" or "VERCEL_ENV" in os.environ

    # 1. Startup: Create database tables if they do not exist (Skip on Vercel)
    if not is_vercel:
        logger.info("Local environment detected. Initializing database tables...")
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logger.info("Database tables initialized.")
        except Exception as e:
            logger.error(f"Error initializing local database tables: {e}")
    else:
        logger.info("Vercel deployment environment detected. Skipping automatic table migration.")

    # 2. Startup: Load tickets and initialize Bloom Filter
    try:
        logger.info("Initializing Bloom Filter from database...")
        async with async_session_maker() as session:
            await bloom_service.initialize_from_db(session)
        logger.info("Bloom Filter initialized successfully.")
    except Exception as e:
        logger.error(f"Database error during Bloom Filter startup initialization: {e}")
        logger.warning("Application starting up without pre-initialized Bloom Filter cache.")
        
    yield
    # 3. Shutdown: Dispose database engine connections
    logger.info("Shutting down engine...")
    try:
        await engine.dispose()
    except Exception as e:
        logger.error(f"Error disposing database engine on shutdown: {e}")

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="A production-ready Ticket Management System optimized with a Bloom Filter search cache.",
    version="1.0.0",
    lifespan=lifespan
)

# API Health Check Endpoint (useful for verifying Vercel & Supabase connection health)
@app.get("/api/health", include_in_schema=False)
async def health_check():
    from sqlalchemy import text
    try:
        async with async_session_maker() as session:
            await session.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        logger.error(f"Database health check query failed: {e}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"status": "unhealthy", "error": str(e)}
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
