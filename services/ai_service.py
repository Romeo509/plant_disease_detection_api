"""
AI service for plant condition analysis using NVIDIA API
"""
import base64
import json
import requests
from typing import Dict, Any


class PlantAnalysisService:
    """Service for analyzing plant conditions using NVIDIA's vision AI"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.api_url = "https://integrate.api.nvidia.com/v1/chat/completions"
        self.model = "meta/llama-3.2-90b-vision-instruct"
    
    def get_analysis_prompt(self) -> str:
        """Get the detailed prompt for plant condition analysis"""
        return (
            "You are an AI plant health analyst. Analyze the uploaded image or video.\n\n"
            "**Your job is to detect ONLY maize (corn) plants from Ghana.**\n"
            "- If the image is not a maize plant (e.g., banana or others), respond with:\n"
            "  1. Plant type: Not maize\n"
            "  2. Disease status: Not applicable\n"
            "  3. Control or treatment: Not applicable\n\n"
            "**If it is maize, check only for the following problems:**\n"
            "- Maize Streak Virus → yellowish leaf streaks, stunted growth\n"
            "- Northern Corn Leaf Blight → long, gray/tan, cigar-shaped lesions on lower leaves\n"
            "- Common Rust → many small, round reddish-brown pustules on leaves\n"
            "- Fall Armyworm → chewed leaves, 'windowpane' damage, frass in whorls, visible worm/larvae\n"
            "- Stem Borers → holes in stalks or cobs, broken stems, weak plants\n"
            "- Maize Weevils → holed or damaged grains (post-harvest pest)\n\n"
            "**Detection rules:**\n"
            "- Use your AI vision to identify the plant and disease\n"
            "- If a worm or larvae is visible on maize, classify it as **Fall Armyworm**\n"
            "- If no visible symptoms match any known issue, reply 'Healthy'\n"
            "- Do **not** guess. Identify only based on clear visual symptoms\n"
            "- Give **only one** diagnosis per image\n"
            "- Do **not** use vague terms like 'worm' or 'caterpillar'. Use exact names\n"
            "- Do **not** suggest handpicking pests\n\n"
            "**For maize issues, suggest control or treatment (2–3 lines max) using real-world, local-friendly advice:**\n"
            "- Approved pesticides: emamectin benzoate, neem, tebuconazole\n"
            "- Early planting, crop rotation, resistant maize varieties\n"
            "- Proper field hygiene and post-harvest drying/storage\n\n"
        )
    
    def encode_image(self, file_path: str) -> str:
        """Encode image file to base64 string"""
        with open(file_path, "rb") as f:
            return base64.b64encode(f.read()).decode()
    
    def create_payload(self, image_b64: str, file_ext: str) -> Dict[str, Any]:
        """Create API payload for plant analysis"""
        prompt = self.get_analysis_prompt()
        image_tag = f'<img src="data:image/{file_ext};base64,{image_b64}" />'
        
        return {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": prompt + image_tag
                }
            ],
            "max_tokens": 512,
            "temperature": 1.00,
            "top_p": 1.00,
            "frequency_penalty": 0.00,
            "presence_penalty": 0.00,
            "stream": True
        }
    
    def get_headers(self) -> Dict[str, str]:
        """Get API request headers"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "text/event-stream"
        }
    
    def process_streaming_response(self, response) -> str:
        """Process streaming response from NVIDIA API"""
        full_response = ""
        
        for line in response.iter_lines():
            if line:
                decoded_line = line.decode("utf-8")
                if decoded_line.startswith("data: "):
                    data = decoded_line[6:]  # Remove "data: " prefix
                    if data != "[DONE]":
                        try:
                            json_data = json.loads(data)
                            if "choices" in json_data and len(json_data["choices"]) > 0:
                                delta = json_data["choices"][0].get("delta", {})
                                if "content" in delta:
                                    full_response += delta["content"]
                        except json.JSONDecodeError:
                            # If JSON parsing fails, just append the raw data
                            full_response += data
        
        # If we didn't get a proper streaming response, try to parse as JSON
        if not full_response and response.status_code == 200:
            try:
                json_response = response.json()
                if "choices" in json_response and len(json_response["choices"]) > 0:
                    full_response = json_response["choices"][0].get("message", {}).get("content", "")
            except json.JSONDecodeError:
                pass
        
        return full_response
    
    def analyze_plant_image(self, file_path: str, file_ext: str) -> str:
        """
        Analyze plant image using NVIDIA API
        Returns: Raw AI response text
        """
        image_b64 = self.encode_image(file_path)
        payload = self.create_payload(image_b64, file_ext)
        headers = self.get_headers()
        
        response = requests.post(self.api_url, headers=headers, json=payload, stream=True)
        response.raise_for_status()
        
        return self.process_streaming_response(response)