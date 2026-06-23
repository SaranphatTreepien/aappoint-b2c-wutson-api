# models.py
from pydantic import BaseModel
from typing import Optional


class BookingRequest(BaseModel):
    shop_id: int
    service_id: int
    party_size: int
    start_sec: int
    duration_sec: int
    zone_id: str
    # contact info (required for Path A)
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


async def step1_availability(
    shop_id: int,
    service_id: int,
    start_date: str,
    end_date: Optional[str] = None,
    party_size: Optional[int] = 2,
):
    params = {
        "shop_id": shop_id,
        "service_id": service_id,
        "start_date": start_date,
    }
    if end_date:
        params["end_date"] = end_date
    if party_size:
        params["party_size"] = party_size


class VerifyRequest(BaseModel):
    shop_id: int
    event_id: int
    po_id: int


class BookingResponse(BaseModel):
    status: str  # success / pending_payment / failed / fallback
    path: str  # A / B
    redirect_url: Optional[str] = None
    checkout_url: Optional[str] = None
    event_id: Optional[int] = None
    po_id: Optional[int] = None
    total_price: Optional[str] = None
    total_deposit: Optional[str] = None
    error: Optional[str] = None
