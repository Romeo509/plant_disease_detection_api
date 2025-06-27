from flask import Flask, request, render_template, jsonify
import uuid, requests, os, json
from typing import List, Dict, Optional
from pathlib import Path
from werkzeug.utils import secure_filename
from datetime import datetime
import logging
from config import Config

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

kNvcfAssetUrl = "https://api.nvcf.nvidia.com/v2/nvcf/assets"
INVOKE_URL = "https://ai.api.nvidia.com/v1/vlm/nvidia/vila"

kSupportedList = {
    "png": ["image/png", "img"],
    "jpg": ["image/jpg", "img"],
    "jpeg": ["image/jpeg", "img"],
    "webp": ["image/webp", "img"],
    "bmp": ["image/bmp", "img"],
    "mp4": ["video/mp4", "video"],
    "avi": ["video/avi", "video"],
    "mov": ["video/mov", "video"]
}

# Comprehensive plant disease database
PLANT_DISEASES = {
    "corn": {
        "diseases": [
            {
                "name": "Northern Corn Leaf Blight",
                "symptoms": "Long, cigar-shaped, gray to tan lesions (1-6 inches) with distinct borders, parallel to leaf veins",
                "pathogen": "Exserohilum turcicum",
                "severity_indicators": ["lesion size", "leaf coverage", "plant stage"]
            },
            {
                "name": "Southern Corn Leaf Blight", 
                "symptoms": "Small, rectangular tan lesions with dark borders, parallel to veins",
                "pathogen": "Bipolaris maydis",
                "severity_indicators": ["number of lesions", "leaf yellowing"]
            },
            {
                "name": "Common Rust",
                "symptoms": "Small, circular to oval, reddish-brown pustules scattered on leaves",
                "pathogen": "Puccinia sorghi",
                "severity_indicators": ["pustule density", "leaf coverage"]
            },
            {
                "name": "Gray Leaf Spot",
                "symptoms": "Rectangular, gray to tan lesions with yellow halos, confined by leaf veins",
                "pathogen": "Cercospora zeae-maydis",
                "severity_indicators": ["lesion count", "yellowing extent"]
            },
            {
                "name": "Maize Streak Virus",
                "symptoms": "Yellow to white streaks parallel to leaf veins, stunted growth",
                "pathogen": "Maize streak virus",
                "severity_indicators": ["streak coverage", "plant stunting"]
            },
            {
                "name": "Fall Armyworm",
                "symptoms": "Chewed leaves with 'windowpane' effect, frass in whorl, visible larvae",
                "pathogen": "Spodoptera frugiperda",
                "severity_indicators": ["feeding damage extent", "larval presence"]
            },
            {
                "name": "Stem Borers",
                "symptoms": "Entry holes in stems, broken/lodged plants, sawdust-like frass",
                "pathogen": "Various lepidopteran species",
                "severity_indicators": ["hole count", "stem damage", "lodging"]
            }
        ],
        "treatments": {
            "Northern Corn Leaf Blight": "Apply fungicides (tebuconazole, propiconazole). Plant resistant varieties. Ensure good field drainage and air circulation. Remove crop debris.",
            "Southern Corn Leaf Blight": "Use resistant hybrids. Apply fungicides early. Practice crop rotation with non-host crops. Manage crop residue.",
            "Common Rust": "Plant resistant varieties. Apply fungicides (tebuconazole, azoxystrobin) when pustules appear. Avoid overhead irrigation.",
            "Gray Leaf Spot": "Use resistant hybrids. Apply fungicides preventively. Improve air circulation. Practice minimum tillage.",
            "Maize Streak Virus": "Control leafhopper vectors with insecticides. Plant resistant varieties. Remove infected plants early.",
            "Fall Armyworm": "Apply Bt-based insecticides or emamectin benzoate. Use pheromone traps. Practice early planting. Remove egg masses.",
            "Stem Borers": "Apply carbofuran or chlorpyrifos at whorl stage. Use resistant varieties. Practice field sanitation. Intercrop with legumes."
        }
    },
    "tomato": {
        "diseases": [
            {
                "name": "Early Blight",
                "symptoms": "Dark brown spots with concentric rings on lower leaves, yellowing",
                "pathogen": "Alternaria solani",
                "severity_indicators": ["spot size", "ring patterns", "defoliation"]
            },
            {
                "name": "Late Blight",
                "symptoms": "Water-soaked lesions with white fuzzy growth on leaf undersides",
                "pathogen": "Phytophthora infestans", 
                "severity_indicators": ["lesion spread", "white growth", "fruit rot"]
            },
            {
                "name": "Bacterial Wilt",
                "symptoms": "Wilting without yellowing, brown vascular discoloration",
                "pathogen": "Ralstonia solanacearum",
                "severity_indicators": ["wilting speed", "vascular browning"]
            },
            {
                "name": "Mosaic Virus",
                "symptoms": "Mottled yellow-green patterns on leaves, stunted growth",
                "pathogen": "Tobacco mosaic virus",
                "severity_indicators": ["mottling extent", "stunting severity"]
            }
        ],
        "treatments": {
            "Early Blight": "Apply copper-based fungicides or mancozeb. Improve air circulation. Water at soil level. Remove affected leaves.",
            "Late Blight": "Apply metalaxyl or copper fungicides preventively. Ensure good drainage. Avoid overhead watering in humid conditions.",
            "Bacterial Wilt": "Use resistant varieties. Practice crop rotation. Improve soil drainage. Remove infected plants immediately.",
            "Mosaic Virus": "Control aphid vectors. Use resistant varieties. Sanitize tools. Remove infected plants."
        }
    }
}

def get_ext(filename: str) -> str:
    return filename.split(".")[-1].lower()

def mime_type(ext: str) -> str:
    return kSupportedList.get(ext, ["application/octet-stream"])[0]

def media_type(ext: str) -> str:
    return kSupportedList.get(ext, ["unknown", "unknown"])[1]

def _upload_asset(file_path: str, description: str) -> str:
    """Upload file to NVIDIA asset storage"""
    ext = get_ext(file_path)
    try:
        with open(file_path, "rb") as f:
            headers = {
                "Authorization": f"Bearer {app.config['NVIDIA_API_KEY']}",
                "Content-Type": "application/json",
                "accept": "application/json"
            }
            
            auth_response = requests.post(kNvcfAssetUrl, headers=headers, json={
                "contentType": mime_type(ext), 
                "description": description
            }, timeout=30)

            auth_response.raise_for_status()
            auth_json = auth_response.json()

            upload_response = requests.put(
                auth_json["uploadUrl"],
                data=f,
                headers={
                    "x-amz-meta-nvcf-asset-description": description,
                    "content-type": mime_type(ext)
                },
                timeout=60
            )
            upload_response.raise_for_status()
            
            logger.info(f"Successfully uploaded asset: {auth_json['assetId']}")
            return auth_json["assetId"]
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Upload failed: {str(e)}")
        raise Exception(f"File upload failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected upload error: {str(e)}")
        raise

def _delete_asset(asset_id: str) -> None:
    """Delete asset from NVIDIA storage"""
    try:
        headers = {"Authorization": f"Bearer {app.config['NVIDIA_API_KEY']}"}
        response = requests.delete(f"{kNvcfAssetUrl}/{asset_id}", headers=headers, timeout=30)
        logger.info(f"Asset {asset_id} deletion status: {response.status_code}")
    except Exception as e:
        logger.warning(f"Failed to delete asset {asset_id}: {str(e)}")

def create_enhanced_prompt() -> str:
    """Create a comprehensive AI prompt for plant disease detection"""
    return """You are an expert plant pathologist specializing in disease identification for agricultural crops, particularly in tropical and subtropical regions like Ghana.

ANALYSIS INSTRUCTIONS:
1. **Plant Identification**: First identify the plant species. Focus on major crops: corn/maize, tomato, pepper, cassava, yam, plantain, cocoa, rice, beans, okra.

2. **Disease/Pest Detection**: Look for these specific symptoms:
   
   FOR CORN/MAIZE:
   - Northern Corn Leaf Blight: Long (1-6 inch), cigar-shaped, gray-tan lesions with distinct borders
   - Southern Corn Leaf Blight: Small rectangular tan lesions with dark borders
   - Common Rust: Small circular reddish-brown pustules scattered on leaves
   - Gray Leaf Spot: Rectangular gray lesions with yellow halos between veins
   - Maize Streak Virus: Yellow-white streaks parallel to veins, stunted plants
   - Fall Armyworm: Chewed leaves with "windowpane" holes, frass in whorls, larvae visible
   - Stem Borers: Entry holes in stems, sawdust-like frass, broken stems
   
   FOR TOMATO:
   - Early Blight: Dark spots with concentric rings, yellowing lower leaves
   - Late Blight: Water-soaked lesions, white fuzzy growth underneath
   - Bacterial Wilt: Sudden wilting without yellowing, brown vascular tissue
   - Mosaic Virus: Mottled yellow-green leaf patterns, stunted growth
   
   FOR OTHER CROPS:
   - Look for common symptoms: spots, wilting, discoloration, holes, growths, stunting

3. **Severity Assessment**: Rate as Mild (1-25% affected), Moderate (26-50%), Severe (51-75%), or Critical (>75%)

4. **Environmental Factors**: Consider if visible - humidity signs, water stress, nutrient deficiency symptoms

RESPONSE FORMAT:
Plant Type: [Species name]
Health Status: [Healthy/Diseased - if diseased, specify condition]
Disease/Pest: [Specific name or "None detected"]
Severity: [Mild/Moderate/Severe/Critical or N/A]
Confidence: [High/Medium/Low - based on symptom clarity]
Key Symptoms: [List 2-3 most important visible symptoms]
Recommended Treatment: [Specific actionable advice for local farmers]
Prevention: [2-3 preventive measures]

IMPORTANT RULES:
- Only diagnose what you can clearly see
- If symptoms are unclear, state "Inconclusive - requires closer examination"
- Don't guess - it's better to say "unidentified condition" than misdiagnose
- Consider multiple possible causes if symptoms overlap
- Prioritize treatments available to small-scale farmers in Ghana
- Include both chemical and organic/cultural control options when possible"""

def parse_enhanced_response(content: str) -> Dict:
    """Parse the enhanced AI response into structured data"""
    lines = [line.strip() for line in content.strip().split('\n') if line.strip()]
    
    result = {
        'plant_type': 'Unknown',
        'health_status': 'Unknown',
        'disease_pest': 'None detected',
        'severity': 'N/A',
        'confidence': 'Unknown',
        'key_symptoms': 'No symptoms identified',
        'treatment': 'No treatment needed',
        'prevention': 'General plant care recommended',
        'analysis_timestamp': datetime.now().isoformat()
    }
    
    current_field = None
    
    for line in lines:
        # Check for field headers
        if ':' in line:
            parts = line.split(':', 1)
            field_name = parts[0].lower().strip()
            field_value = parts[1].strip() if len(parts) > 1 else ''
            
            if 'plant type' in field_name or 'plant species' in field_name:
                current_field = 'plant_type'
                if field_value:
                    result['plant_type'] = field_value
            elif 'health status' in field_name or 'status' in field_name:
                current_field = 'health_status'
                if field_value:
                    result['health_status'] = field_value
            elif 'disease' in field_name or 'pest' in field_name:
                current_field = 'disease_pest'
                if field_value:
                    result['disease_pest'] = field_value
            elif 'severity' in field_name:
                current_field = 'severity'
                if field_value:
                    result['severity'] = field_value
            elif 'confidence' in field_name:
                current_field = 'confidence'
                if field_value:
                    result['confidence'] = field_value
            elif 'symptom' in field_name:
                current_field = 'key_symptoms'
                if field_value:
                    result['key_symptoms'] = field_value
            elif 'treatment' in field_name or 'control' in field_name:
                current_field = 'treatment'
                if field_value:
                    result['treatment'] = field_value
            elif 'prevention' in field_name or 'preventive' in field_name:
                current_field = 'prevention'
                if field_value:
                    result['prevention'] = field_value
        elif current_field and line and not any(x in line.lower() for x in ['plant type', 'health status', 'disease', 'severity', 'confidence', 'symptom', 'treatment', 'prevention']):
            # Continue previous field
            if result[current_field] in ['Unknown', 'None detected', 'No symptoms identified', 'No treatment needed', 'General plant care recommended']:
                result[current_field] = line
            else:
                result[current_field] += ' ' + line
    
    return result

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/demo')
def api_docs():
    return render_template('demo.html')

@app.route('/api/info')
def api_info():
    return jsonify({
        'name': 'Enhanced Plant Disease Detection API',
        'version': '2.0.0',
        'description': 'Advanced AI-powered plant disease identification with comprehensive analysis',
        'supported_plants': list(PLANT_DISEASES.keys()) + ['pepper', 'cassava', 'yam', 'plantain', 'cocoa', 'rice', 'beans', 'okra'],
        'features': [
            'Multi-plant species recognition',
            'Disease severity assessment',
            'Confidence scoring',
            'Localized treatment recommendations',
            'Prevention strategies',
            'Environmental factor consideration'
        ],
        'endpoints': {
            'POST /analyze': {
                'description': 'Comprehensive plant health analysis',
                'parameters': {
                    'media': 'multipart/form-data - One or more image/video files',
                    'plant_type': 'optional string - Expected plant type for focused analysis'
                },
                'supported_formats': list(kSupportedList.keys()),
                'max_file_size': '16MB per file',
                'response_format': {
                    'success': 'boolean',
                    'analysis': {
                        'plant_type': 'string',
                        'health_status': 'string',
                        'disease_pest': 'string',
                        'severity': 'string',
                        'confidence': 'string',
                        'key_symptoms': 'string',
                        'treatment': 'string',
                        'prevention': 'string',
                        'analysis_timestamp': 'ISO datetime'
                    },
                    'raw_response': 'string',
                    'processing_info': {
                        'files_processed': 'number',
                        'processing_time': 'seconds'
                    }
                }
            }
        }
    })

@app.route('/api/diseases')
def get_diseases():
    """Get available disease information"""
    return jsonify(PLANT_DISEASES)

@app.route('/analyze', methods=['POST'])
def analyze_plant():
    start_time = datetime.now()
    
    if 'media' not in request.files:
        return jsonify({'error': 'No media files uploaded', 'success': False}), 400

    files = request.files.getlist('media')
    if not files or all(f.filename == '' for f in files):
        return jsonify({'error': 'No valid media files selected', 'success': False}), 400

    # Optional plant type hint
    expected_plant = request.form.get('plant_type', '').strip()
    
    # Validate file types and sizes
    valid_files = []
    for file in files:
        if file.filename == '':
            continue
            
        ext = get_ext(file.filename)
        if ext not in kSupportedList:
            return jsonify({
                'error': f'Unsupported file format: {ext}. Supported: {list(kSupportedList.keys())}',
                'success': False
            }), 400
            
        # Check file size (16MB limit)
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > 16 * 1024 * 1024:
            return jsonify({
                'error': f'File {file.filename} exceeds 16MB limit',
                'success': False
            }), 400
            
        valid_files.append(file)

    if not valid_files:
        return jsonify({'error': 'No valid files to process', 'success': False}), 400

    asset_ids, media_tags, file_paths = [], [], []
    
    try:
        # Process files
        for file in valid_files:
            ext = get_ext(file.filename)
            filename = f"{uuid.uuid4()}.{ext}"
            path = os.path.join(UPLOAD_FOLDER, filename)
            file.save(path)

            asset_id = _upload_asset(path, f"Plant analysis - {file.filename}")
            asset_ids.append(asset_id)
            file_paths.append(path)
            media_tags.append(f'<{media_type(ext)} src="data:{mime_type(ext)};asset_id,{asset_id}" />')

        # Prepare enhanced prompt
        prompt = create_enhanced_prompt()
        if expected_plant:
            prompt += f"\n\nNOTE: User expects this to be a {expected_plant} plant. Focus analysis accordingly but verify the plant type first."

        # API call to NVIDIA
        headers = {
            "Authorization": f"Bearer {app.config['NVIDIA_API_KEY']}",
            "Content-Type": "application/json",
            "NVCF-INPUT-ASSET-REFERENCES": ",".join(asset_ids),
            "NVCF-FUNCTION-ASSET-IDS": ",".join(asset_ids),
            "Accept": "application/json"
        }

        payload = {
            "max_tokens": 1500,  # Increased for detailed analysis
            "temperature": 0.1,   # Lower for more consistent results
            "top_p": 0.8,
            "seed": 42,
            "messages": [{
                "role": "user",
                "content": f"{prompt}\n\nAnalyze these images: {' '.join(media_tags)}"
            }],
            "stream": False,
            "model": "nvidia/vila"
        }

        logger.info(f"Sending request to NVIDIA API with {len(asset_ids)} assets")
        
        response = requests.post(INVOKE_URL, headers=headers, json=payload, timeout=120)
        response.raise_for_status()
        result = response.json()

        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            parsed_result = parse_enhanced_response(content)
            
            processing_time = (datetime.now() - start_time).total_seconds()
            
            return jsonify({
                'success': True,
                'analysis': parsed_result,
                'raw_response': content,
                'processing_info': {
                    'files_processed': len(valid_files),
                    'processing_time': round(processing_time, 2)
                }
            })
        else:
            logger.error(f"No choices in API response: {result}")
            return jsonify({
                'error': 'No response from AI model',
                'success': False,
                'api_response': result
            }), 500

    except requests.exceptions.Timeout:
        return jsonify({
            'error': 'Analysis request timed out. Please try with smaller images.',
            'success': False
        }), 408
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API request failed: {str(e)}")
        return jsonify({
            'error': f'API request failed: {str(e)}',
            'success': False
        }), 500
        
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return jsonify({
            'error': f'Analysis failed: {str(e)}',
            'success': False
        }), 500

    finally:
        # Cleanup
        for asset_id in asset_ids:
            try:
                _delete_asset(asset_id)
            except Exception as e:
                logger.warning(f"Failed to delete asset {asset_id}: {str(e)}")
                
        for path in file_paths:
            try:
                if os.path.exists(path):
                    os.remove(path)
                    logger.info(f"Deleted temporary file: {path}")
            except Exception as e:
                logger.warning(f"Failed to delete file {path}: {str(e)}")

@app.errorhandler(413)
def too_large(e):
    return jsonify({
        'error': 'File too large. Maximum size is 16MB per file.',
        'success': False
    }), 413

@app.errorhandler(500)
def internal_error(e):
    return jsonify({
        'error': 'Internal server error. Please try again later.',
        'success': False
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"Starting Enhanced Plant Disease Detection API on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)  # Disable debug in production
