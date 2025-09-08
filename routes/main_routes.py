"""
Main routes for the plant disease detection API
"""
import os
from flask import Blueprint, request, render_template, jsonify, current_app
from services.ai_service import PlantAnalysisService
from services.response_parser import PlantConditionParser
from services.api_info_service import ApiInfoService
from utils.file_utils import save_uploaded_file, cleanup_file, is_supported_format

# Create blueprint for main routes
main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    """Render main page"""
    return render_template('index.html')


@main_bp.route('/demo')
def api_docs():
    """Render API documentation page"""
    return render_template('demo.html')


@main_bp.route('/api/info')
def api_info():
    """Get API information and documentation"""
    return jsonify(ApiInfoService.get_api_info())


@main_bp.route('/analyze', methods=['POST'])
def analyze_plant():
    """
    Analyze plant media files for condition identification
    Returns: JSON response with analysis results
    """
    # Validate request has files
    if 'media' not in request.files:
        return jsonify({'error': 'No media files uploaded'}), 400

    files = request.files.getlist('media')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No media files selected'}), 400

    file_path = None
    
    try:
        file = files[0]
        
        # Validate file format
        if not is_supported_format(file.filename):
            return jsonify({'error': f'{file.filename} format not supported'}), 400

        # Save uploaded file
        file_path, ext = save_uploaded_file(file)
        
        # Initialize AI service
        ai_service = PlantAnalysisService(current_app.config['NVIDIA_API_KEY'])
        
        # Get AI analysis
        raw_response = ai_service.analyze_plant_image(file_path, ext)
        
        # Parse response to structured format
        parser = PlantConditionParser()
        parsed_result = parser.parse_ai_response(raw_response)
        
        return jsonify({
            'success': True,
            'analysis': parsed_result,
            'raw_response': raw_response
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        # Cleanup uploaded file
        if file_path:
            cleanup_file(file_path)