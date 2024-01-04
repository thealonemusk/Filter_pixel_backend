from fastapi import FastAPI, HTTPException
from PIL import Image
from starlette.responses import FileResponse
from exif import Image as ExifImage
import os
import rawpy
import json

app = FastAPI()
RAW_IMAGE_DIR = 'raw_images'
CONVERTED_IMAGE_DIR = 'converted_images'
PROCESS_INFO_FILE = 'process_info.json'
SUPPORTED_EXTENSIONS = ['.IIQ', '.3FR', '.DCR', '.K25', '.KDC', '.CRW', '.CR2', '.CR3', '.ERF', '.MEF', '.MOS', '.NEF', '.NRW', '.ORF', '.PEF', '.RW2', '.ARW', '.SRF', '.SR2', '.DNG']

def process_image(file_path):
    exif_info = {}
    try:
        with open(file_path, 'rb') as image_file:
            img = ExifImage(image_file)
            for tag, value in img.exif.items():
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
    raw_files = [file_name for file_name in os.listdir(directory) if any(file_name.upper().endswith(ext) for ext in SUPPORTED_EXTENSIONS)]
    return raw_files

def needs_processing(raw_file_path, converted_file_path):
    process_info = get_process_info()
    raw_last_modified = os.path.getmtime(raw_file_path)
    return process_info.get(raw_file_path, 0) < raw_last_modified or not os.path.exists(converted_file_path)

def update_process_info(raw_file_path, timestamp):
    process_info = get_process_info()
    process_info[raw_file_path] = timestamp
    with open(PROCESS_INFO_FILE, 'w') as f:
        json.dump(process_info, f)

def get_process_info():
    process_info = {}
    if os.path.exists(PROCESS_INFO_FILE):
        try:
            with open(PROCESS_INFO_FILE, 'r') as f:
                process_info = json.load(f)
        except json.JSONDecodeError:
            pass
    return process_info

@app.get('/images')
async def get_images():
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

    return {'images': image_list}

@app.get('/image-preview/{filename}')
async def get_image_preview(filename: str):
    file_path = os.path.join(CONVERTED_IMAGE_DIR, filename.replace(os.path.splitext(filename)[1], '.jpg'))
    if needs_processing(os.path.join(RAW_IMAGE_DIR, filename), file_path):
        raw_file_path = os.path.join(RAW_IMAGE_DIR, filename)
        preview_generator = create_preview_generator(raw_file_path)
        create_preview(file_path, preview_generator)
        update_process_info(raw_file_path, os.path.getmtime(raw_file_path))

    return StreamingResponse(open(file_path, "rb"), media_type='image/jpeg')

@app.get('/download/{filename}')
async def download_image(filename: str):
    file_path = os.path.join(RAW_IMAGE_DIR, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="File not found")
    return FileResponse(file_path, media_type='application/octet-stream', filename=filename)

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host='0.0.0.0', port=8000)
