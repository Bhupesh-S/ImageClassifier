import os
import uvicorn
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException, Query
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from analyzer import CivicIssueAnalyzer, ConfigurationError, APIResponseError

# ------------------------------
# Jharkhand District Classification
# ------------------------------
jharkhand_districts = [
    "Bokaro", "Chatra", "Deoghar", "Dhanbad", "Dumka", "East Singhbhum",
    "Garhwa", "Giridih", "Godda", "Gumla", "Hazaribagh", "Jamtara", "Khunti",
    "Koderma", "Latehar", "Lohardaga", "Pakur", "Palamu", "Ramgarh", "Ranchi",
    "Sahebganj", "Saraikela Kharsawan", "Simdega", "West Singhbhum"
]

def classify_location(address: str) -> str:
    address_lower = address.lower()
    if "jharkhand" not in address_lower:
        return "Not in Jharkhand"
    for district in jharkhand_districts:
        if district.lower() in address_lower:
            return district
    return "Jharkhand (District Unknown)"

# ------------------------------
# Load Environment Variables
# ------------------------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ConfigurationError("Google API key not found in .env file. Please add GOOGLE_API_KEY.")

# ------------------------------
# FastAPI App Setup
# ------------------------------
app = FastAPI(
    title="Indian Civic Issue Analyzer API",
    description="API for analyzing civic issues from uploaded images using Gemini AI.",
    version="1.0.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://yourdomain.com",
        "http://localhost:19006",
        "http://10.0.2.16:19006"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize Analyzer
analyzer = CivicIssueAnalyzer(api_key=GOOGLE_API_KEY)

# ------------------------------
# API Endpoints
# ------------------------------
@app.get("/")
def root():
    """Root endpoint to check API status."""
    return {"message": "Indian Civic Issue Analyzer API is running 🚀"}


@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Upload an image to analyze the civic issue.
    """
    allowed_extensions = {".jpg", ".jpeg", ".png", ".webp"}
    max_file_size = 5 * 1024 * 1024  # 5 MB
    suffix = os.path.splitext(file.filename)[1].lower()
    if suffix not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Invalid file type. Only images are allowed.")
    contents = await file.read()
    if len(contents) > max_file_size:
        raise HTTPException(status_code=400, detail="File too large. Max size is 5MB.")

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp_file:
            tmp_file.write(contents)
            tmp_file_path = tmp_file.name

        result = analyzer.analyze_image(tmp_file_path)

        if os.path.exists(tmp_file_path):
            os.remove(tmp_file_path)

        if "error" in result:
            raise HTTPException(status_code=500, detail="Analysis failed.")
        return JSONResponse(content=result)

    except (ConfigurationError, APIResponseError):
        raise HTTPException(status_code=400, detail="Configuration or API error.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")


@app.get("/classify-district")
def classify_district(address: str = Query(..., description="Full location address")):
    """
    Classify the Jharkhand district from a given location address.
    """
    district = classify_location(address)
    return {"address": address, "district": district}


# ------------------------------
# Run App
# ------------------------------
if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
