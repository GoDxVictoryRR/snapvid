"""SnapVid server entry point."""
import uvicorn
from snapreel.server import app

if __name__ == "__main__":
    uvicorn.run("snapreel.server:app", host="0.0.0.0", port=8000, reload=False)
