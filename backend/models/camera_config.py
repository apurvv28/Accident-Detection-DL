("""Camera configuration model (minimal).""")
from typing import Optional, Dict

from pydantic import BaseModel


class CameraConfig(BaseModel):
	camera_id: str
	name: Optional[str] = None
	stream_url: Optional[str] = None
	location: Optional[Dict] = None
	status: Optional[str] = "active"


__all__ = ["CameraConfig"]

