"""
API info service for handling API documentation and metadata
"""
from typing import Dict, Any


class ApiInfoService:
    """Service for providing API information and documentation"""
    
    @staticmethod
    def get_api_info() -> Dict[str, Any]:
        """Get comprehensive API information and documentation"""
        return {
            'name': 'Plant Condition Identifier API',
            'version': '1.0.0',
            'description': 'AI-powered plant condition identification and treatment recommendation system',
            'endpoints': {
                'POST /analyze': {
                    'description': 'Analyze plant media files for plant condition identification',
                    'parameters': {
                        'media': 'multipart/form-data - One or more image/video files'
                    },
                    'supported_formats': ['jpg', 'jpeg', 'png', 'mp4'],
                    'max_file_size': '16MB',
                    'response_format': {
                        'success': 'boolean',
                        'analysis': {
                            'plant_type': 'string',
                            'disease_status': 'string', 
                            'control_treatment': 'string'
                        },
                        'raw_response': 'string'
                    }
                },
                'GET /docs': {
                    'description': 'API documentation page'
                },
                'GET /api/info': {
                    'description': 'API information and endpoint details'
                }
            },
            'example_usage': {
                'curl': 'curl -X POST http://localhost:5000/analyze -F "media=@plant_image.jpg"',
                'python': 'requests.post("http://localhost:5000/analyze", files={"media": open("plant.jpg", "rb")})'
            }
        }