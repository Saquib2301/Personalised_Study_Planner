"""
SmartStudy AI - Server Entrypoint.
Mounts FastAPI REST API, static files, and database initialization.
"""

import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from backend.database import init_db
from backend.routes import router as api_router

# Initialize database tables
init_db()

app = FastAPI(
    title="SmartStudy AI — Personalised Study Planner",
    description="Intelligent study planner with AI roadmaps, accountability, and dynamic re-scheduling",
    version="2.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router)

# Mount static folder
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_index():
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "SmartStudy AI API is running. index.html not yet found."}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    print("\n==================================================================")
    print(f" [INFO] SMARTSTUDY AI SERVER STARTING ON http://localhost:{port}")
    print("==================================================================\n")
    uvicorn.run("server:app", host="0.0.0.0", port=port, reload=True)
