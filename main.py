
import os
import re
import glob
import shutil
import tempfile
from urllib.parse import urlparse

import yt_dlp

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from yt_dlp.utils import DownloadError

app = FastAPI(title="Social Media Video Downloader")

# CORS
origins = os.getenv("ALLOWED_ORIGIN", "*").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[x.strip() for x in origins],
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["*"],
)

# Platform yang didukung
ALLOWED_DOMAINS = (
    "facebook.com",
    "fb.watch",
    "tiktok.com",
    "instagram.com",
)

def valid_url(url):
    try:
        parsed = urlparse(url)
        host = (parsed.hostname or "").lower()

        return (
            parsed.scheme == "https"
            and any(
                host == domain or host.endswith("." + domain)
                for domain in ALLOWED_DOMAINS
            )
        )
    except Exception:
        return False


@app.get("/")
def home():
    return {
        "status": "online",
        "message": "Social Media Video Downloader siap digunakan",
        "platforms": ["Facebook", "TikTok", "Instagram"],
        "quality": "720p"
    }


@app.get("/download")
def download_video(
    url: str = Query(...),
    format: str = Query("720p")
):
    if not valid_url(url):
        raise HTTPException(
            status_code=400,
            detail="Tautan Facebook, TikTok, atau Instagram tidak valid."
        )

    temp_dir = tempfile.mkdtemp(prefix="video_")

    try:
        
        video_format = (
            "bestvideo[height<=720]+bestaudio/"
            "best[height<=720]/best"
        )


        options = {
            "format": video_format,
            "outtmpl": os.path.join(
                temp_dir,
                "%(title).80s-%(id)s.%(ext)s"
            ),
            "noplaylist": True,
            "quiet": True,
            "no_warnings": True,
            "restrictfilenames": True,
            "socket_timeout": 20,
            "retries": 2,
            "fragment_retries": 2,
            "max_filesize": 500 * 1024 * 1024,
        }

        with yt_dlp.YoutubeDL(options) as ydl:
            info = ydl.extract_info(url, download=True)

            title = info.get("title") or "video"

        files = [
            f for f in glob.glob(os.path.join(temp_dir, "*"))
            if os.path.isfile(f)
            and not f.endswith((".part", ".ytdl", ".json"))
        ]

        if not files:
            raise Exception("File video tidak ditemukan.")

        video_path = max(files, key=os.path.getsize)

        filename = re.sub(
            r'[\\/:*?"<>|]',
            "_",
            title
        )[:80]

        filename = filename.strip(" ._") or "video"
        filename += os.path.splitext(video_path)[1]

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

    except DownloadError as e:
        shutil.rmtree(temp_dir, ignore_errors=True)

        message = str(e).lower()

        if any(word in message for word in [
            "login", "registered users",
            "cookies", "authentication",
            "private"
        ]):
            detail = (
                "Video membutuhkan login atau akses khusus. "
                "Server hanya dapat memproses video yang "
                "dapat diakses secara sah tanpa login."
            )
        else:
            detail = (
                "Video gagal diproses. Periksa tautan "
                "dan coba lagi."
            )

        raise HTTPException(
            status_code=422,
            detail=detail
        )

    except Exception:
        shutil.rmtree(temp_dir, ignore_errors=True)

        raise HTTPException(
            status_code=500,
            detail="Terjadi kesalahan saat memproses video."
        )
