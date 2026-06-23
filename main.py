# main.py
from fastapi import FastAPI, HTTPException
from models import BookingRequest, AvailabilityRequest, VerifyRequest, BookingResponse
from aappoint import step1_availability, book_path_b, book_path_a, step4_verify, PATH_B

app = FastAPI(title="Dr.Watson AAppoint Middleware")


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/availability")
async def check_availability(req: AvailabilityRequest):
    try:
        result = await step1_availability(
            req.shop_id, req.service_id, req.start_date, req.end_date, req.party_size
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/book", response_model=BookingResponse)
async def book(req: BookingRequest):
    try:
        # Route Path B vs Path A
        if (req.shop_id, req.service_id) in PATH_B:
            result = await book_path_b(
                req.shop_id, req.service_id, req.start_sec, req.party_size
            )
        else:
            # Path A requires contact info
            if not all([req.first_name, req.last_name, req.email, req.phone]):
                raise HTTPException(
                    status_code=422,
                    detail="Path A requires first_name, last_name, email, phone",
                )
            result = await book_path_a(
                req, req.start_sec, req.zone_id, req.duration_sec
            )

        return BookingResponse(**result)

    except ValueError as e:
        error_msg = str(e)
        # Fallback conditions
        if "username-exists" in error_msg or "product-unavailable" in error_msg:
            redirect_url = f"https://marketplace-dev.aappoint.me/rwg/{req.shop_id}/service/{req.service_id}"
            return BookingResponse(
                status="fallback", path="A", redirect_url=redirect_url, error=error_msg
            )
        raise HTTPException(status_code=400, detail=error_msg)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/verify")
async def verify_payment(req: VerifyRequest):
    try:
        result = await step4_verify(req.shop_id, req.event_id, req.po_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))
