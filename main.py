# main.py
import os
import uvicorn
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from analyzer import CivicIssueAnalyzer, ConfigurationError, APIResponseError

# --- Load environment variables from .env ---
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ConfigurationError("Google API key not found in .env file. Please add GOOGLE_API_KEY.")

# --- FastAPI App ---
app = FastAPI(
    title="Indian Civic Issue Analyzer API",
    description="API for analyzing civic issues from uploaded images using Gemini AI.",
    version="1.0.0"
)

# --- CORS Configuration ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize Analyzer ---
analyzer = CivicIssueAnalyzer(api_key=GOOGLE_API_KEY)

# --- Mappings for user-friendly text ---
ISSUE_TYPE_MAP = {
    "damaged_road": "Pothole / Damaged Road",
    "pothole": "Pothole",
    "waste_dump": "Garbage / Waste Dump",
    "streetlight_fault": "Streetlight not working",
    "water_leak": "Water Leakage",
    "graffiti": "Graffiti",
    "sewage_overflow": "Sewage Overflow",
    "tree_fall": "Fallen Tree",
    "drainage_block": "Blocked Drainage",
    "unknown_issue": "Unidentified Issue"
}

SEVERITY_MESSAGES = {
    "low": "It is not urgent but should be resolved soon.",
    "medium": "It may cause inconvenience if not fixed in time.",
    "high": "It is critical and needs urgent attention."
}


@app.get("/")
def root():
    return {"message": "Indian Civic Issue Analyzer API is running 🚀"}


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """Upload an image to analyze the civic issue."""
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    max_file_size = 5 * 1024 * 1024  # 5 MB

    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")

    contents = await file.read()
    if len(contents) > max_file_size:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5MB.")

    try:
        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(contents)
            tmp_file_path = tmp_file.name

        # Analyze with CivicIssueAnalyzer
        result = analyzer.analyze_image(tmp_file_path)

        # Cleanup temp file
        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

        if "error" in result:
            raise HTTPException(status_code=500, detail="Analysis failed.")

        # Map issue type to readable label
        issue_type = result.get("issue_type", "unknown_issue")
        readable_issue = ISSUE_TYPE_MAP.get(issue_type, issue_type.replace("_", " ").capitalize())
        result["issue_type"] = issue_type
        result["issue_label"] = readable_issue

        # Handle severity
        severity = result.get("severity", "medium").lower()
        severity_msg = SEVERITY_MESSAGES.get(severity, "Severity not specified.")

        # Generate natural description
        result["description"] = result.get("description", "").strip()
        if not result["description"]:
    # Fallback only if Gemini fails
            result["description"] = f"A {readable_issue.lower()} was detected. {severity_msg}"

        return JSONResponse(content=result)

    except (ConfigurationError, APIResponseError):
        raise HTTPException(status_code=400, detail="Configuration or API error.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Unexpected server error: {str(e)}")


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

