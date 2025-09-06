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
    allow_origins=[
        "https://yourdomain.com",           # Web frontend
        "http://localhost:19006",           # Expo Go local dev
        "http://10.0.2.16:19006"         # Expo Go on LAN (replace with your actual port if different           # Optional: local web dev
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Initialize Analyzer ---
analyzer = CivicIssueAnalyzer(api_key=GOOGLE_API_KEY)


@app.get("/")
def root():
    """Root endpoint to check API status."""
    return {"message": "Indian Civic Issue Analyzer API is running 🚀"}



@app.post("/analyze")
async def analyze_image(file: UploadFile = File(...)):
    """
    Upload an image to analyze the civic issue.
    """
    # --- Security: Restrict file type and size ---
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

        # Return result
        if "error" in result:
            # Sanitize error message
            raise HTTPException(status_code=500, detail="Analysis failed.")
        return JSONResponse(content=result)

    except (ConfigurationError, APIResponseError) as e:
        raise HTTPException(status_code=400, detail="Configuration or API error.")
    except Exception:
        raise HTTPException(status_code=500, detail="Unexpected server error.")


if __name__ == "__main__":
    # Run the FastAPI app
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
