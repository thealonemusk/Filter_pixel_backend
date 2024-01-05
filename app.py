from flask import Flask, jsonify, send_file
from flask_cors import CORS
from image_processor import process_image, create_preview, get_supported_raw_files, needs_processing, update_process_info
import os
import json

# RAW_IMAGE_DIR = 'raw_images'
# CONVERTED_IMAGE_DIR = 'converted_images'
# PROCESS_INFO_FILE = 'process_info.json'

app = Flask(__name__)
CORS(app)
RAW_IMAGE_DIR = 'raw_images'
CONVERTED_IMAGE_DIR = 'converted_images'
PROCESS_INFO_FILE = 'process_info.json'

# app = Flask(__name__)
# CORS(app)
# IMAGE_DIR = 'images'

def process_image(file_path):
    exif_info = {}
    try:
        with open(file_path, 'rb') as image_file:
            tags = process_file(image_file)
            for tag, value in tags.items():
                if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
                    exif_info[str(tag)] = str(value)
    except Exception as e:
        print(f"Error processing image: {e}")
    return exif_info

def create_preview(file_path, preview_path):
    try:
        with rawpy.imread(file_path) as raw:
            rgb = raw.postprocess()
            converted_image = Image.fromarray(rgb)
            converted_image.thumbnail((2000, 2000))
            converted_image.save(preview_path, 'JPEG')
    except Exception as e:
        print(f"Error creating preview: {e}")

def get_supported_raw_files(directory):
    supported_extensions = ['.IIQ', '.3FR', '.DCR', '.K25', '.KDC', '.CRW', '.CR2','.CR3', '.ERF', '.MEF', '.MOS', '.NEF', '.NRW', '.ORF', '.PEF', '.RW2', '.ARW', '.SRF', '.SR2' , '.DNG']
    raw_files = [file_name for file_name in os.listdir(directory) if any(file_name.upper().endswith(ext) for ext in supported_extensions)]
    return raw_files

def get_process_info():
    process_info = {}
    if os.path.exists(PROCESS_INFO_FILE):
        try:
            with open(PROCESS_INFO_FILE, 'r') as f:
                process_info = json.load(f)
        except json.JSONDecodeError:
            pass
    return process_info

def needs_processing(raw_file_path, converted_file_path):
    process_info = get_process_info()
    raw_last_modified = os.path.getmtime(raw_file_path)
    return process_info.get(raw_file_path, 0) < raw_last_modified or not os.path.exists(converted_file_path)

def update_process_info(raw_file_path, timestamp):
    process_info = get_process_info()
    process_info[raw_file_path] = timestamp
    with open(PROCESS_INFO_FILE, 'w') as f:
        json.dump(process_info, f)

def get_exif_data(file_path):
    exif_info = {}
    try:
        image = Image.open(file_path)
        exif = image._getexif()
        if exif:
            for tag, value in exif.items():
                decoded_tag = TAGS.get(tag, tag)
                exif_info[decoded_tag] = value
    except Exception as e:
        print(f"Error getting EXIF data: {e}")
    return exif_info

@app.route('/images')
def get_images():
    image_list = []
    raw_files = get_supported_raw_files(RAW_IMAGE_DIR)
    
    for file_name in raw_files:
        raw_file_path = os.path.join(RAW_IMAGE_DIR, file_name)
        converted_file_path = os.path.join(CONVERTED_IMAGE_DIR, file_name.replace(os.path.splitext(file_name)[1], '.jpg'))
        
        exif_info = process_image(raw_file_path)
        image_list.append({
            'file_name': file_name,
            'exif_info': exif_info
        })

    return jsonify({'images': image_list})

@app.route('/image-preview/<filename>')
def get_image_preview(filename):
    file_path = os.path.join(CONVERTED_IMAGE_DIR, filename.replace(os.path.splitext(filename)[1], '.jpg'))
    if needs_processing(os.path.join(RAW_IMAGE_DIR, filename), file_path):
        raw_file_path = os.path.join(RAW_IMAGE_DIR, filename)
        create_preview(raw_file_path, file_path)
        update_process_info(raw_file_path, os.path.getmtime(raw_file_path))

    return send_file(file_path, mimetype='image/jpeg')


@app.route('/download/<filename>')
def download_image(filename):
    file_path = os.path.join(RAW_IMAGE_DIR, filename)
    if not os.path.exists(file_path):
        return 'File not found', 404
    return send_file(file_path, mimetype='application/octet-stream', as_attachment=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
