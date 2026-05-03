"""
Exam Paper Analyzer — FastAPI Application
Analyzes examination papers against syllabus objectives.
"""

import os
import json
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, UploadFile, Form, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
import aiofiles
from dotenv import load_dotenv

from analyzer import run_analysis

load_dotenv()

app = FastAPI(title="Exam Paper Analyzer", version="1.0.0")
BASE_DIR = Path(__file__).parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze(
    request: Request,
    syllabus: UploadFile = File(...),
    exam_paper: UploadFile = File(...),
    model: str = Form("auto"),
):
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(await syllabus.read())
        syllabus_path = f.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(await exam_paper.read())
        exam_path = f.name

    try:
        result = run_analysis(syllabus_path, exam_path, model_preference=model)
    except Exception as e:
        result = {"error": str(e)}
    finally:
        os.unlink(syllabus_path)
        os.unlink(exam_path)

    return templates.TemplateResponse("results.html", {
        "request": request,
        "result": result,
        "result_json": json.dumps(result, indent=2),
        "syllabus_name": syllabus.filename,
        "exam_name": exam_paper.filename,
    })


@app.post("/api/analyze")
async def api_analyze(
    syllabus: UploadFile = File(...),
    exam_paper: UploadFile = File(...),
    model: str = Form("auto"),
):
    """JSON API endpoint for programmatic access."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(await syllabus.read())
        syllabus_path = f.name

    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(await exam_paper.read())
        exam_path = f.name

    try:
        result = run_analysis(syllabus_path, exam_path, model_preference=model)
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
    finally:
        os.unlink(syllabus_path)
        os.unlink(exam_path)

    return JSONResponse(result)


@app.get("/health")
async def health():
    from analyzer import OCR_AVAILABLE
    return {
        "status": "ok",
        "anthropic_key": bool(os.getenv("ANTHROPIC_API_KEY")),
        "openai_key": bool(os.getenv("OPENAI_API_KEY")),
        "ocr_available": OCR_AVAILABLE,
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
