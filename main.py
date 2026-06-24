# main.py
import json
import logging
from fastapi import FastAPI, HTTPException, Request
from models import BookingRequest, AvailabilityRequest, VerifyRequest, BookingResponse
from aappoint import step1_availability, book_path_b, book_path_a, step4_verify, PATH_B

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)

app = FastAPI(title="Dr.Watson AAppoint Middleware")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/availability")
async def check_availability(
    shop_id: int,
    service_id: int,
    start_date: str,
    end_date: str = None,
    party_size: int = 2,
):
    log.info(
        f"[AVAILABILITY] shop={shop_id} service={service_id} date={start_date}~{end_date} party={party_size}"
    )
    try:
        result = await step1_availability(
            shop_id, service_id, start_date, end_date, party_size
        )
        slots = result.get("available_slots", [])
        log.info(f"[AVAILABILITY] OK — {len(slots)} days returned")
        return {"available_slots": slots}
    except Exception as e:
        log.error(f"[AVAILABILITY] ERROR — {e}")
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/book", response_model=BookingResponse)
async def book(req: BookingRequest):
    log.info("=" * 60)
    log.info(f"[BOOK] REQUEST — shop={req.shop_id} service={req.service_id}")
    log.info(
        f"[BOOK] party={req.party_size} start_sec={req.start_sec} zone_id='{req.zone_id}'"
    )
    if req.first_name:
        log.info(
            f"[BOOK] contact={req.first_name} {req.last_name} | {req.email} | {req.phone}"
        )

    try:
        if (req.shop_id, req.service_id) in PATH_B:
            log.info("[BOOK] PATH B (free)")
            result = await book_path_b(
                req.shop_id,
                req.service_id,
                req.start_sec,
                req.party_size,
                req.zone_id,
            )
        else:
            log.info("[BOOK] PATH A (deposit)")
            if not all([req.first_name, req.last_name, req.email, req.phone]):
                raise HTTPException(
                    status_code=422,
                    detail="Path A requires first_name, last_name, email, phone",
                )
            result = await book_path_a(
                req, req.start_sec, req.zone_id, req.duration_sec
            )

        log.info(f"[BOOK] RESULT — status={result.get('status')}")
        if result.get("event_id"):
            log.info(f"[BOOK] event_id={result['event_id']} po_id={result['po_id']}")
        if result.get("checkout_url"):
            log.info(f"[BOOK] checkout_url={result['checkout_url'][:80]}...")
        if result.get("redirect_url"):
            log.info(f"[BOOK] redirect_url={result['redirect_url']}")
        log.info("=" * 60)

        return BookingResponse(**result)

    except HTTPException:
        raise
    except Exception as e:
        import traceback

        log.error(f"[BOOK] ERROR — {e}")
        log.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify")
async def verify_payment(req: VerifyRequest):
    log.info(f"[VERIFY] shop={req.shop_id} event_id={req.event_id} po_id={req.po_id}")
    try:
        result = await step4_verify(req.shop_id, req.event_id, req.po_id)
        log.info(f"[VERIFY] RESULT — {result}")
        return result
    except Exception as e:
        log.error(f"[VERIFY] ERROR — {e}")
        raise HTTPException(status_code=500, detail=str(e))
