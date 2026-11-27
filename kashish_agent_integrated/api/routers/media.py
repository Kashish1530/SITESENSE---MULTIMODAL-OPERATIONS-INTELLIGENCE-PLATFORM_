"""
SITESENSE - Media Retrieval Router (Feature 1.6)
Serves original and annotated media files for evidence viewing in the UI.
"""

import os
from pathlib import Path
from typing import Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")
DATABASE_URL = os.getenv("DATABASE_URL")

router = APIRouter(tags=["Media"])

@router.get("/media/{id}")
async def get_media_file(id: str, annotated: bool = False):
    """
    API Contract: GET /media/{id}?annotated=true
    Streams the binary image/video file.
    """
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor(cursor_factory=RealDictCursor)

    cur.execute("SELECT id, path, type FROM media WHERE id::text = %s;", (id,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "MEDIA_NOT_FOUND", "message": f"Media '{id}' not found."}}
        )

    file_path = row["path"]
    if not os.path.exists(file_path):
        raise HTTPException(
            status_code=404,
            detail={"error": {"code": "FILE_NOT_FOUND", "message": f"File at '{file_path}' does not exist on disk."}}
        )

    # Determine media mime type
    ext = Path(file_path).suffix.lower()
    media_type = "image/jpeg"
    if ext in [".png"]:
        media_type = "image/png"
    elif ext in [".mp4"]:
        media_type = "video/mp4"
    elif ext in [".pdf"]:
        media_type = "application/pdf"

    return FileResponse(file_path, media_type=media_type)
