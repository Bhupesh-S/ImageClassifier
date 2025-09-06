import os
import json
import logging
from typing import Dict, Any
from PIL import Image
import google.generativeai as genai

# --- Configure structured logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# --- Custom Exceptions for clear error handling ---
class ConfigurationError(Exception):
    """Custom exception for configuration problems."""
    pass

class APIResponseError(Exception):
    """Custom exception for issues with the API response."""
    pass

class CivicIssueAnalyzer:
    """
    A professional-grade client for analyzing civic issues in images.
    It uses Gemini for visual identification and a local mapping file for routing.
    """
    def __init__(self, api_key: str, mapping_file: str = 'mapping.json'):
        """
        Initializes the analyzer by configuring the Gemini client and loading the mapping file.
        
        Args:
            api_key: The Google API key.
            mapping_file: Path to the JSON file containing issue-to-department mappings.
        """
        # --- API Configuration ---
        if not api_key:
            raise ConfigurationError("Google API key not provided.")
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash-latest')

        # --- Load the local mapping file ---
        try:
            with open(mapping_file, 'r') as f:
                self.mapping_data = json.load(f)
            logging.info(f"Successfully loaded mapping data from '{mapping_file}'.")
        except FileNotFoundError:
            raise ConfigurationError(f"Mapping file not found at '{mapping_file}'.")
        except json.JSONDecodeError:
            raise ConfigurationError(f"Error decoding JSON from '{mapping_file}'. Please check its format.")

        # Dynamically create the list of valid issue types from the mapping file keys
        self.VALID_ISSUE_TYPES = list(self.mapping_data.keys())
        self.VALID_SEVERITY = ['high', 'medium', 'low', 'none']

        def _create_prompt(self) -> str:
        """Creates a simplified, focused prompt for the AI."""
            return f"""
            You are a specialized AI assistant for a civic monitoring app. Your only task is to analyze the
            provided image and identify the primary civic issue.

            The JSON object you return must contain exactly four keys:
        1. 'issue_type': Classify the issue from this list: {self.VALID_ISSUE_TYPES}.
        2. 'severity': Rate the issue's severity from this list: {self.VALID_SEVERITY}.
        3. 'confidence': A float between 0.0 and 1.0 for your classification confidence.
        4. 'description': Write 1–2 natural sentences describing the issue in plain language.

        Respond only with the raw JSON object.
        """

        def _validate_ai_response(self, response_text: str) -> Dict[str, Any]:
        """Parses and validates only the JSON response from the Gemini API."""
            try:
                clean_text = response_text.strip().replace("```json", "").replace("```", "").strip()
                data = json.loads(clean_text)
            except json.JSONDecodeError:
                raise APIResponseError(f"Failed to decode API response as JSON. Response: {response_text}")

            required_keys = ['issue_type', 'severity', 'confidence', 'description']
            for key in required_keys:
                if key not in data:
                    raise APIResponseError(f"API response missing required key: '{key}'. Response: {data}")

            if data['issue_type'] not in self.VALID_ISSUE_TYPES:
                logging.warning(f"AI returned an unexpected 'issue_type' label: {data['issue_type']}")

            return data

        def analyze_image(self, image_path: str) -> Dict[str, Any]:
        ...
            ai_result = self._validate_ai_response(response.text)

            issue_type = ai_result.get('issue_type')
            mapping_details = self.mapping_data.get(issue_type, {})

            final_result = {
            **ai_result,
            "department": mapping_details.get("department", "N/A"),
            "responsible": mapping_details.get("responsible", "N/A")
            }
            return final_result


        except Exception as e:
            logging.error(f"An unexpected error occurred during analysis: {e}", exc_info=True)

            return {"error": str(e)}
