# aappoint.py
import httpx
from models import BookingRequest
from typing import Optional

BASE_URL = "https://dev.aappoint.me"

# Path B shops (ฟรี, 2 steps only)
PATH_B = {(241, 400)}


async def step1_availability(
    shop_id: int,
    service_id: int,
    start_date: str,
    end_date: Optional[str] = None,
    party_size: Optional[int] = 2,
):
    url = f"{BASE_URL}/rwg-payment/availability"
    params = {
        "shop_id": shop_id,
        "service_id": service_id,
        "start_date": start_date,
    }
    if end_date:
        params["end_date"] = end_date
    if party_size:
        params["party_size"] = party_size

    print(f"Calling: {url} params={params}")

    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:

        try:
            res = await client.get(url, params=params)
            res.encoding = "utf-8"  # ← เพิ่มบรรทัดนี้
            print(f"Status: {res.status_code}")
            print(f"Body: {res.text}")
            if res.status_code != 200:
                raise ValueError(res.text)
            return res.json()
        except httpx.RequestError as e:
            print(f"Request error: {e}")
            raise


async def step2_get_detail(
    shop_id: int, service_id: int, start_sec: int, party_size: int
):
    url = f"{BASE_URL}/rwg-payment"
    params = {
        "shop_id": shop_id,
        "service_id": service_id,
        "start_sec": start_sec,
        "party_size": party_size,
    }
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:

        res = await client.get(url, params=params)
        res.raise_for_status()
        return res.json()


async def book_path_b(shop_id: int, service_id: int, start_sec: int, party_size: int):
    """Path B: 241/400 only — 2 steps then return redirect_url"""
    # STEP 2 - verify free
    detail = await step2_get_detail(shop_id, service_id, start_sec, party_size)

    if detail["total_price"] != "0" or detail["total_deposit"] != "0":
        raise ValueError(f"Expected free booking but got total={detail['total_price']}")

    redirect_url = (
        f"https://marketplace-dev.aappoint.me/rwg/{shop_id}/service/{service_id}"
    )
    return {
        "status": "success",
        "path": "B",
        "redirect_url": redirect_url,
        "detail": detail,
    }


async def step3_checkout(payload: dict):
    url = f"{BASE_URL}/rwg-payment/checkout"
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:

        res = await client.post(url, json=payload)
        raw = res.text
        if res.status_code != 200:
            raise ValueError(f"STEP 3 failed: {raw}")
        return res.json()


async def step4_verify(shop_id: int, event_id: int, po_id: int):
    url = f"{BASE_URL}/rwg-payment/payment-result"
    params = {"shop_id": shop_id, "event_id": event_id, "po_id": po_id}
    async with httpx.AsyncClient(verify=False, timeout=30.0) as client:

        res = await client.get(url, params=params)
        res.raise_for_status()
        return res.json()


async def book_path_a(
    req: BookingRequest, start_sec: int, zone_id: str, duration_sec: int
):
    # STEP 2
    detail = await step2_get_detail(
        req.shop_id, req.service_id, start_sec, req.party_size
    )

    table_id = detail["tables"][0]["id"] if detail.get("tables") else None
    product_id = detail["products"][0]["id"] if detail.get("products") else None

    # STEP 3
    payload = {
        "shop_id": req.shop_id,
        "service_id": req.service_id,
        "start_sec": start_sec,
        "duration_sec": duration_sec,
        "party_size": req.party_size,
        "zone": zone_id,
        "table_id": table_id,
        "selected_products": (
            [{"shop_product_id": product_id, "amount": 1}] if product_id else []
        ),
        "optional_products": [],
        "first_name": req.first_name,
        "last_name": req.last_name,
        "email": req.email,
        "phone": req.phone,
        "accept_late_time": True,
        "accept_no_refund": True,
        "accept_news": False,
        "accept_notification": True,
        "payment_method": "shopeepay",
        "result_url": "https://dev-sui-booking-point-collect-hd3yycn2oq-as.a.run.app/mock",
    }
    checkout = await step3_checkout(payload)
    checkout_url = checkout.get("checkout_url", "").replace("\\u0026", "&")

    return {
        "status": "pending_payment",
        "path": "A",
        "checkout_url": checkout_url,
        "event_id": checkout["event"]["id"],
        "po_id": checkout["purchase_order"]["id"],
        "total_price": detail["total_price"],
        "total_deposit": detail["total_deposit"],
    }
