# aappoint.py
import logging
import httpx
from models import BookingRequest
from typing import Optional

log = logging.getLogger(__name__)

BASE_URL = "https://dev.aappoint.me"
PATH_B = {(241, 400)}

RETRY_SAFE = 3  # availability, detail
RETRY_CHECKOUT = 1  # checkout — ระวังสร้างซ้ำ


async def _get(url: str, params: dict, retries: int = 1) -> dict:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                log.info(f"[GET] {url} params={params} (attempt {attempt})")
                res = await client.get(url, params=params)
                res.encoding = "utf-8"
                log.info(f"[GET] status={res.status_code} body={res.text[:200]}")
                if res.status_code != 200:
                    raise ValueError(f"HTTP {res.status_code}: {res.text}")
                return res.json()
        except (httpx.RequestError, httpx.TimeoutException) as e:
            log.warning(f"[GET] attempt {attempt} failed: {e}")
            last_err = e
    raise last_err or ValueError("GET failed")


async def _post(url: str, payload: dict, retries: int = 1) -> dict:
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            async with httpx.AsyncClient(verify=False, timeout=30.0) as client:
                log.info(f"[POST] {url} (attempt {attempt})")
                log.info(f"[POST] payload={payload}")
                res = await client.post(url, json=payload)
                res.encoding = "utf-8"
                log.info(f"[POST] status={res.status_code} body={res.text[:300]}")
                if res.status_code != 200:
                    raise ValueError(f"HTTP {res.status_code}: {res.text}")
                return res.json()
        except (httpx.RequestError, httpx.TimeoutException) as e:
            log.warning(f"[POST] attempt {attempt} failed: {e}")
            last_err = e
    raise last_err or ValueError("POST failed")


async def step1_availability(
    shop_id: int,
    service_id: int,
    start_date: str,
    end_date: Optional[str] = None,
    party_size: Optional[int] = 2,
):
    params = {"shop_id": shop_id, "service_id": service_id, "start_date": start_date}
    if end_date:
        params["end_date"] = end_date
    if party_size:
        params["party_size"] = party_size
    return await _get(
        f"{BASE_URL}/rwg-payment/availability", params, retries=RETRY_SAFE
    )


async def step2_get_detail(
    shop_id: int, service_id: int, start_sec: int, party_size: int, zone_id: str
):
    params = {
        "shop_id": shop_id,
        "service_id": service_id,
        "start_sec": start_sec,
        "party_size": party_size,
        "zone": zone_id,
    }
    return await _get(f"{BASE_URL}/rwg-payment", params, retries=RETRY_SAFE)


async def step3_checkout(payload: dict):
    return await _post(
        f"{BASE_URL}/rwg-payment/checkout", payload, retries=RETRY_CHECKOUT
    )


async def step4_verify(shop_id: int, event_id: int, po_id: int):
    params = {"shop_id": shop_id, "event_id": event_id, "po_id": po_id}
    return await _get(f"{BASE_URL}/rwg-payment/payment-result", params, retries=1)


async def book_path_b(
    shop_id: int, service_id: int, start_sec: int, party_size: int, zone_id: str
):
    """Path B: 241/400 — ต้อง checkout ด้วย แต่ total=0"""
    log.info(f"[PATH B] shop={shop_id} service={service_id} zone='{zone_id}'")

    # STEP 2 — verify ว่าฟรีจริง
    detail = await step2_get_detail(shop_id, service_id, start_sec, party_size, zone_id)
    log.info(
        f"[PATH B] total_price={detail['total_price']} total_deposit={detail['total_deposit']}"
    )

    if detail["total_price"] != "0" or detail["total_deposit"] != "0":
        raise ValueError(f"Expected free booking but got total={detail['total_price']}")

    table_id = detail["tables"][0]["id"] if detail.get("tables") else None
    product_id = detail["products"][0]["id"] if detail.get("products") else None

    # STEP 3 — checkout (required แม้ฟรี)
    payload = {
        "shop_id": shop_id,
        "service_id": service_id,
        "start_sec": start_sec,
        "duration_sec": detail.get("duration_sec", 10800),
        "party_size": party_size,
        "zone": zone_id,
        "table_id": table_id,
        "selected_products": (
            [{"shop_product_id": product_id, "amount": 1}] if product_id else []
        ),
        "optional_products": [],
        "first_name": "Guest",
        "last_name": "Watson",
        "email": "guest@drwatson.ai",
        "phone": "+66000000000",
        "accept_late_time": True,
        "accept_no_refund": True,
        "accept_news": False,
        "accept_notification": True,
        "payment_method": "shopeepay",
        "result_url": "https://dev-sui-booking-point-collect-hd3yycn2oq-as.a.run.app/mock",
    }
    checkout = await step3_checkout(payload)

    event_id = checkout["event"]["id"]
    po_id = checkout["purchase_order"]["id"]

    # redirect_url + query params
    redirect_url = (
        f"https://marketplace-dev.aappoint.me/rwg/{shop_id}/service/{service_id}"
        f"?start_sec={start_sec}&party_size={party_size}&room_id={zone_id}"
    )
    checkout_url = checkout.get("checkout_url", "")
    checkout_url = checkout_url.replace("\\u0026", "&")
    checkout_url = checkout_url.replace("\u0026", "&")

    log.info(f"[PATH B] event_id={event_id} po_id={po_id}")
    log.info(f"[PATH B] checkout_url FULL={checkout_url}")  # เก็บอันนี้อันเดียว
    log.info(f"[PATH B] redirect_url={redirect_url}")
    return {
        "status": "confirmed_pending",
        "path": "B",
        "event_id": event_id,
        "po_id": po_id,
        "checkout_url": checkout_url,
        "redirect_url": redirect_url,
    }


async def book_path_a(
    req: BookingRequest, start_sec: int, zone_id: str, duration_sec: int
):
    """Path A: deposit flow"""
    log.info(f"[PATH A] shop={req.shop_id} service={req.service_id} zone='{zone_id}'")

    # STEP 2
    detail = await step2_get_detail(
        req.shop_id, req.service_id, start_sec, req.party_size, zone_id
    )
    log.info(
        f"[PATH A] total_price={detail['total_price']} total_deposit={detail['total_deposit']}"
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

    event_id = checkout["event"]["id"]
    po_id = checkout["purchase_order"]["id"]
    checkout_url = checkout.get("checkout_url", "")
    checkout_url = checkout_url.replace("\\u0026", "&")
    checkout_url = checkout_url.replace("\u0026", "&")

    log.info(f"[PATH A] event_id={event_id} po_id={po_id}")
    log.info(f"[PATH A] checkout_url FULL={checkout_url}")  # เก็บอันนี้อันเดียว
    return {
        "status": "pending_payment",
        "path": "A",
        "event_id": event_id,
        "po_id": po_id,
        "checkout_url": checkout_url,
        "total_price": detail["total_price"],
        "total_deposit": detail["total_deposit"],
    }
