from typing import Optional

from pydantic import BaseModel


class CityResponse(BaseModel):
    id: int
    name: str

    full_name: Optional[str] = None

    region_id: Optional[int] = None
    region_name: Optional[str] = None

    district_id: Optional[int] = None
    district_name: Optional[str] = None

    settlement_type_id: Optional[int] = None
    settlement_type_name: Optional[str] = None

    model_config = {
        "from_attributes": False,
    }