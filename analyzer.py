import os
import json
import logging
from typing import Dict, Any
from PIL import Image
import google.generativeai as genai

# --- Logging configuration ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Custom exceptions ---
class ConfigurationError(Exception):
    pass

class APIResponseError(Exception):
    pass

class CivicIssueAnalyzer:
    """
    Analyzer for civic issues using Gemini AI and local mapping.json.
    Ensures category selection is always valid according to mapping.json.
    """
    def __init__(self, api_key: str, mapping_file: str = 'mapping.json'):
        if not api_key:
            raise ConfigurationError("Google API key not provided.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # Load mapping.json
        try:
            with open(mapping_file, 'r') as f:
                self.mapping_data = json.load(f)
            logging.info(f"Loaded mapping data from '{mapping_file}'.")
        except FileNotFoundError:
            raise ConfigurationError(f"Mapping file not found at '{mapping_file}'.")
        except json.JSONDecodeError:
            raise ConfigurationError(f"Error decoding mapping.json. Check its format.")

        # Valid categories and severities
        self.VALID_ISSUE_TYPES = list(self.mapping_data.keys())
        self.VALID_SEVERITY = ['high', 'medium', 'low', 'none']

    def _create_prompt(self) -> str:
        """Prompt Gemini to output a valid JSON with description."""
        return f"""
        You are an AI for a civic monitoring app. Analyze the image and classify the primary issue.
        Respond ONLY with a JSON object with four keys:
        1. 'issue_type': Pick ONE from {self.VALID_ISSUE_TYPES}.
        2. 'severity': One of {self.VALID_SEVERITY}.
        3. 'confidence': Float 0.0 to 1.0.
        4. 'description': 1–2 natural sentences describing the issue.

        Do not invent any other categories.
        Respond only with the raw JSON.
        """

    def _validate_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parse and validate Gemini's JSON response."""
        try:
            clean_text = response_text.strip().replace("```json", "").replace("```", "").strip()
            data = json.loads(clean_text)
        except json.JSONDecodeError:
            raise APIResponseError(f"Failed to parse JSON from AI response: {response_text}")

        # Ensure all keys exist
        required_keys = ['issue_type', 'severity', 'confidence', 'description']
        for key in required_keys:
            if key not in data:
                raise APIResponseError(f"Missing key '{key}' in AI response: {data}")

        # Ensure issue_type is valid
        if data['issue_type'] not in self.VALID_ISSUE_TYPES:
            logging.warning(f"Invalid category '{data['issue_type']}', defaulting to 'unknown_issue'")
            data['issue_type'] = "unknown_issue"

        return data

    def analyze_image(self, image_path: str) -> Dict[str, Any]:
        """Analyze image and enrich result with mapping.json details."""
        logging.info(f"Analyzing image: {image_path}")
        if not os.path.exists(image_path):
            return {"error": "Image file not found."}

        try:
            with Image.open(image_path) as img:
                prompt = self._create_prompt()
                response = self.model.generate_content([prompt, img], generation_config={"temperature": 0.2})

            ai_result = self._validate_ai_response(response.text)

            # Set department/responsible based on mapping.json
            category = ai_result['issue_type']
            mapping_details = self.mapping_data.get(category, {})
            final_result = {
                **ai_result,
                "department": mapping_details.get("department", "N/A"),
                "responsible": mapping_details.get("responsible", "N/A")
            }

            return final_result

        except Exception as e:
            logging.error(f"Unexpected error during analysis: {e}", exc_info=True)
            return {"error": str(e)}
