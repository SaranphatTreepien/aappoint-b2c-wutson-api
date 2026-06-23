drwatson-middleware/
├── main.py          # FastAPI app + routes
├── aappoint.py      # AAppoint API calls (STEP 1-4)
├── models.py        # Request/Response schemas
├── requirements.txt
└── render.yaml      # Deploy config สำหรับ Render

แต่ละไฟล์ทำอะไร
aappoint.py — core logic ทั้งหมด

Path B: STEP 1 + 2 → return redirect_url
Path A: STEP 1 → 2 → 3 → 3.5 → 4

models.py — Pydantic schemas

BookingRequest, BookingResponse

main.py — routes

POST /book → router ไป Path A หรือ B อัตโนมัติ

render.yaml — deploy config บน Render