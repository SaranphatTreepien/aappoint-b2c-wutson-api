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
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class AvailabilityRequest(BaseModel):
    shop_id: int
    service_id: int
    start_date: str
    end_date: Optional[str] = None
    party_size: Optional[int] = 2


class VerifyRequest(BaseModel):
    shop_id: int
    event_id: int
    po_id: int


class BookingResponse(BaseModel):
    # status values:
    # confirmed_pending — Path B (free, event created, รอ user verify)
    # pending_payment   — Path A (deposit, รอ user จ่าย ShopeePay)
    # fallback          — จองผ่าน API ไม่ได้ ส่ง redirect_url แทน
    # failed            — error
    status: str
    path: str
    redirect_url: Optional[str] = None
    checkout_url: Optional[str] = None
    event_id: Optional[int] = None
    po_id: Optional[int] = None
    total_price: Optional[str] = None
    total_deposit: Optional[str] = None
    error: Optional[str] = None
