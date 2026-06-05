"""
Entry point: python main.py
"""
import uvicorn
from config import get_settings

if __name__ == "__main__":
    s = get_settings()
    uvicorn.run(
        "api.app:app",
        host=s.host,
        port=s.port,
        log_level=s.log_level,
        reload=True,
    )
