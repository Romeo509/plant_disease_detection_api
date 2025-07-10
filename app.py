from flask import Flask, request, render_template, jsonify
import uuid, requests, os, base64
from typing import List
from pathlib import Path
from werkzeug.utils import secure_filename
from config import Config

app = Flask(__name__)
app.config.from_object(Config)

UPLOAD_FOLDER = "uploads"
Path(UPLOAD_FOLDER).mkdir(exist_ok=True)

INVOKE_URL = "https://integrate.api.nvidia.com/v1/chat/completions"

kSupportedList = {
    "png": ["image/png", "img"],
    "jpg": ["image/jpg", "img"],
    "jpeg": ["image/jpeg", "img"],
    "mp4": ["video/mp4", "video"],
}

def get_ext(filename): 
    return filename.split(".")[-1].lower()

def parse_ai_response(content):
    lines = content.strip().split('\n')
    result = {
        'plant_type': 'Unknown',
        'disease_status': 'Unknown',
        'control_treatment': 'No treatment information available'
    }

    current_section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith('1.') and 'plant type' in line.lower():
            current_section = 'plant_type'
            parts = line.split(':', 1)
            if len(parts) > 1:
                result['plant_type'] = parts[1].strip()
        elif line.startswith('2.') and 'disease status' in line.lower():
            current_section = 'disease_status'
            parts = line.split(':', 1)
            if len(parts) > 1:
                result['disease_status'] = parts[1].strip()
        elif line.startswith('3.') and ('control' in line.lower() or 'treatment' in line.lower()):
            current_section = 'control_treatment'
            parts = line.split(':', 1)
            if len(parts) > 1:
                result['control_treatment'] = parts[1].strip()
        elif current_section and not line.startswith(('1.', '2.', '3.')):
            if result[current_section] in ['Unknown', 'No treatment information available']:
                result[current_section] = line
            else:
                result[current_section] += ' ' + line

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
        'name': 'Plant Disease Identifier API',
        'version': '1.0.0',
        'description': 'AI-powered plant disease identification and treatment recommendation system',
        'endpoints': {
            'POST /analyze': {
                'description': 'Analyze plant media files for disease identification',
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
    })

@app.route('/analyze', methods=['POST'])
def analyze_plant():
    if 'media' not in request.files:
        return jsonify({'error': 'No media files uploaded'}), 400

    files = request.files.getlist('media')
    if not files or files[0].filename == '':
        return jsonify({'error': 'No media files selected'}), 400

    query = (
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
        "**Respond exactly like this:**\n"
        "1. Plant type:\n"
        "2. Disease status:\n"
        "3. Control or treatment:"
    )

    try:
        file = files[0]
        ext = get_ext(file.filename)
        if ext not in kSupportedList:
            return jsonify({'error': f'{file.filename} format not supported'}), 400

        filename = f"{uuid.uuid4()}.{ext}"
        path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(path)

        with open(path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()

        headers = {
            "Authorization": f"Bearer {app.config['NVIDIA_API_KEY']}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

        payload = {
            "model": "nvidia/llama-3.1-nemotron-nano-vl-8b-v1",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        { "type": "image_url", "image_url": { "url": f"data:image/{ext};base64,{image_b64}" } },
                        { "type": "text", "text": query }
                    ]
                }
            ],
            "temperature": 1.00,
            "top_p": 0.01,
            "max_tokens": 1024,
            "stream": False
        }

        res = requests.post(INVOKE_URL, headers=headers, json=payload)
        result = res.json()

        if 'choices' in result and len(result['choices']) > 0:
            content = result['choices'][0]['message']['content']
            parsed_result = parse_ai_response(content)
            return jsonify({
                'success': True,
                'analysis': parsed_result,
                'raw_response': content
            })
        else:
            return jsonify({'error': 'No response from AI model'}), 500

    except Exception as e:
        return jsonify({'error': str(e)}), 500

    finally:
        if os.path.exists(path):
            try:
                os.remove(path)
            except:
                pass

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
