"""
FastAPI Main Application
========================

Main entry point for the Claude Discussion Room server.
"""

# Load environment variables from .env file first
from dotenv import load_dotenv
load_dotenv()

import asyncio
import logging
import sys
from contextlib import asynccontextmanager
from pathlib import Path

# Fix for Windows subprocess support
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .routers import history_router, rooms_router
from .websocket import room_websocket
from .services.discussion_orchestrator import cleanup_all_orchestrators
from .models.database import get_engine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Paths - Support both development and packaged installation
ROOT_DIR = Path(__file__).parent.parent
UI_DIST_DIR = ROOT_DIR / "frontend" / "dist"

# Alternative locations for packaged installation
if not UI_DIST_DIR.exists():
    # Try relative to the backend package
    UI_DIST_DIR = Path(__file__).parent / ".." / "frontend" / "dist"
    if not UI_DIST_DIR.exists():
        UI_DIST_DIR = None  # No frontend dist available


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown."""
    # Startup - initialize database
    get_engine()
    logger.info("Database initialized")

    yield

    # Shutdown - cleanup all orchestrators
    await cleanup_all_orchestrators()
    logger.info("Cleanup complete")


# Create FastAPI app
app = FastAPI(
    title="Claude Discussion Room",
    description="Multi-Claude discussion platform with ClaudeCode context",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8888",
        "http://127.0.0.1:8888",
        "http://localhost:9000",
        "http://127.0.0.1:9000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(history_router)
app.include_router(rooms_router)


# WebSocket endpoint
@app.websocket("/ws/rooms/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: int):
    """WebSocket endpoint for discussion room updates."""
    await room_websocket(websocket, room_id)


# Health check
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


# SDK availability check
@app.get("/api/config/available-agents")
async def get_available_agents():
    """Check which agent SDKs are installed and available."""
    available = []

    # Check ClaudeCode SDK
    try:
        from claude_agent_sdk import ClaudeSDKClient
        available.append("claude")
    except ImportError:
        pass

    # Check Codex SDK
    try:
        from codex_sdk import Codex
        available.append("codex")
    except ImportError:
        pass

    return {"available_agents": available}


# Static file serving (Production)
if UI_DIST_DIR and UI_DIST_DIR.exists():
    app.mount("/assets", StaticFiles(directory=UI_DIST_DIR / "assets"), name="assets")

    @app.get("/")
    async def serve_index():
        """Serve the React app index.html."""
        return FileResponse(UI_DIST_DIR / "index.html")

    @app.get("/{path:path}")
    async def serve_spa(path: str):
        """Serve static files or fall back to index.html for SPA routing."""
        if path.startswith("api/") or path.startswith("ws/"):
            return {"error": "Not found"}

        file_path = (UI_DIST_DIR / path).resolve()

        # Prevent path traversal
        try:
            file_path.relative_to(UI_DIST_DIR.resolve())
        except ValueError:
            return FileResponse(UI_DIST_DIR / "index.html")

        if file_path.exists() and file_path.is_file():
            return FileResponse(file_path)

        return FileResponse(UI_DIST_DIR / "index.html")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host="127.0.0.1",
        port=8888,
        reload=True,
    )
