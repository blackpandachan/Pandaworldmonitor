from pydantic import BaseModel


class GeoPoint(BaseModel):
    latitude: float
    longitude: float
