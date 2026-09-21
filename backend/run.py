"""
Convenience launcher — run from the backend/ directory:

    python run.py
    python run.py --port 8080 --reload
"""
import argparse
import uvicorn
from dotenv import load_dotenv

load_dotenv()  # load .env before uvicorn imports app

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Start the RAG API server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true", help="Enable hot-reload (dev only)")
    args = parser.parse_args()

    uvicorn.run(
        "app.main:app",
        host=args.host,
        port=args.port,
        reload=args.reload,
        log_level="info",
    )
