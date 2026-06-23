# main.py
from fastapi import FastAPI, HTTPException
from models import BookingRequest, AvailabilityRequest, VerifyRequest, BookingResponse
from aappoint import step1_availability, book_path_b, book_path_a, step4_verify, PATH_B

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
    try:
        result = await step1_availability(
            shop_id, service_id, start_date, end_date, party_size
        )
        return {"available_slots": result.get("available_slots", [])}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/book", response_model=BookingResponse)
async def book(req: BookingRequest):
    try:
        print("=" * 80)
        print("BOOK REQUEST")
        print(req.model_dump())
        print("=" * 80)

        if (req.shop_id, req.service_id) in PATH_B:
            print("PATH B")

            result = await book_path_b(
                req.shop_id,
                req.service_id,
                req.start_sec,
                req.party_size,
                req.zone_id,
            )

        else:
            print("PATH A")

            if not all([req.first_name, req.last_name, req.email, req.phone]):
                raise HTTPException(
                    status_code=422,
                    detail="Path A requires first_name, last_name, email, phone",
                )

            result = await book_path_a(
                req,
                req.start_sec,
                req.zone_id,
                req.duration_sec,
            )

        print("BOOK RESULT")
        print(result)

        return BookingResponse(**result)

    except Exception as e:
        import traceback

        print("BOOK ERROR")
        traceback.print_exc()

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


@app.post("/verify")
async def verify_payment(req: VerifyRequest):
    try:
        result = await step4_verify(req.shop_id, req.event_id, req.po_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
