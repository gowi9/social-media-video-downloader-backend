
import os
import re
import shutil
import tempfile

import yt_dlp
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

app = FastAPI(title="Social Media Video Downloader")

# CORS configuration
origins = os.getenv("ALLOWED_ORIGIN", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Social Media Video Downloader API siap digunakan"
    }

@app.get("/download")
def download_video(
    url: str = Query(...),
    format: str = Query("best")
):
    if not url.startswith(("http://", "https://")):
        raise HTTPException(
            status_code=400,
            detail="URL tidak valid"
        )

    temp_dir = tempfile.mkdtemp(prefix="video_")

    try:
        options = {
            "format": "bestvideo[height<=720]+bestaudio/best[height<=720]",
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

        files = [
            f for f in os.listdir(temp_dir)
            if os.path.isfile(os.path.join(temp_dir, f))
            and not f.endswith((".part", ".ytdl", ".json"))
        ]

        if not files:
            raise Exception("File video tidak ditemukan")

        video_path = os.path.join(temp_dir, files[0])

        title = info.get("title", "video")
        title = re.sub(r'[\\/:*?"<>|]', "_", title)
        filename = title[:100] + ".mp4"

        return FileResponse(
            path=video_path,
            filename=filename,
            media_type="application/octet-stream",
            background=BackgroundTask(
                shutil.rmtree,
                temp_dir,
                ignore_errors=True
            )
        )

    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        raise HTTPException(
            status_code=400,
            detail=f"Gagal mengunduh video: {str(e)}"
        )

