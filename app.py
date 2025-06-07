# app.py (ฉบับปรับปรุงใหม่)
import os
import json
import threading
import subprocess
import time
import sys
from flask import Flask, render_template, request, jsonify, Response, send_file, send_from_directory
from werkzeug.utils import secure_filename
import logging

# ตั้งค่า logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 📦 ตั้งค่าโฟลเดอร์ของ Flask
app = Flask(__name__,
            template_folder='templates',
            static_folder='static')

# การตั้งค่า
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # จำกัดขนาดไฟล์ 16MB
ALLOWED_FONT_EXTENSIONS = {'.ttf', '.otf'}
ALLOWED_TEXT_EXTENSIONS = {'.txt'}

# 🗂️ สร้างโครงสร้างโฟลเดอร์ที่สมบูรณ์
BASE_FOLDERS = ['fonts', 'corpus', 'dataset', 'models', 'training_scripts', 'logs']
for folder in BASE_FOLDERS:
    os.makedirs(folder, exist_ok=True)

# สร้างโฟลเดอร์ static ถ้ายังไม่มี
os.makedirs('static/css', exist_ok=True)
os.makedirs('static/js', exist_ok=True)
os.makedirs('templates', exist_ok=True)

# ตรวจสอบไฟล์ที่จำเป็น
def check_required_files():
    """ตรวจสอบว่ามีไฟล์ที่จำเป็นครบหรือไม่"""
    required_files = {
        'training_scripts/generate_dataset.py': 'ไฟล์สร้าง dataset',
        'training_scripts/train_ocr.py': 'ไฟล์ฝึกสอนโมเดล'
    }
    
    missing_files = []
    for filepath, description in required_files.items():
        if not os.path.exists(filepath):
            missing_files.append(f"{description} ({filepath})")
    
    return missing_files

# 📄 หน้าแรก
@app.route('/')
def index():
    missing_files = check_required_files()
    if missing_files:
        logger.warning(f"Missing files: {missing_files}")
    return render_template('index.html')

# 📤 อัปโหลดฟอนต์ (ปรับปรุง)
@app.route('/upload/font', methods=['POST'])
def upload_font():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "ไม่พบไฟล์"}), 400
        
        files = request.files.getlist('file')
        uploaded_files = []
        
        for file in files:
            if file and file.filename:
                filename = secure_filename(file.filename)
                file_ext = os.path.splitext(filename)[1].lower()
                
                if file_ext not in ALLOWED_FONT_EXTENSIONS:
                    continue
                
                filepath = os.path.join('fonts', filename)
                file.save(filepath)
                uploaded_files.append(filename)
                logger.info(f"Uploaded font: {filename}")
        
        if uploaded_files:
            return jsonify({
                "success": True, 
                "files": uploaded_files,
                "message": f"อัปโหลดสำเร็จ {len(uploaded_files)} ไฟล์"
            })
        else:
            return jsonify({"success": False, "error": "ไม่มีไฟล์ที่ถูกต้อง"}), 400
            
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 📤 อัปโหลดไฟล์ corpus (ปรับปรุง)
@app.route('/upload/corpus', methods=['POST'])
def upload_corpus():
    try:
        if 'file' not in request.files:
            return jsonify({"success": False, "error": "ไม่พบไฟล์"}), 400
        
        file = request.files['file']
        if file and file.filename:
            filename = secure_filename(file.filename)
            file_ext = os.path.splitext(filename)[1].lower()
            
            if file_ext not in ALLOWED_TEXT_EXTENSIONS:
                return jsonify({"success": False, "error": "รองรับเฉพาะไฟล์ .txt"}), 400
            
            filepath = os.path.join('corpus', 'lao_corpus.txt')
            file.save(filepath)
            
            # อ่านและแสดงสถิติ
            with open(filepath, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            logger.info(f"Uploaded corpus with {len(lines)} lines")
            
            return jsonify({
                "success": True,
                "stats": {
                    "lines": len(lines),
                    "filename": filename
                }
            })
        
        return jsonify({"success": False, "error": "ไฟล์ไม่ถูกต้อง"}), 400
        
    except Exception as e:
        logger.error(f"Corpus upload error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 📜 ลิสต์ฟอนต์พร้อมรายละเอียด
@app.route('/list/fonts', methods=['GET'])
def list_fonts():
    try:
        files = []
        font_dir = 'fonts'
        
        for filename in os.listdir(font_dir):
            if os.path.splitext(filename)[1].lower() in ALLOWED_FONT_EXTENSIONS:
                filepath = os.path.join(font_dir, filename)
                file_size = os.path.getsize(filepath)
                files.append({
                    "name": filename,
                    "size": f"{file_size / 1024:.1f} KB"
                })
        
        return jsonify({
            "success": True, 
            "files": files,
            "total": len(files)
        })
    except Exception as e:
        logger.error(f"List fonts error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 📊 ตรวจสอบสถานะระบบ
@app.route('/system/status', methods=['GET'])
def system_status():
    """ตรวจสอบสถานะความพร้อมของระบบ"""
    status = {
        "ready": True,
        "checks": {}
    }
    
    # ตรวจสอบไฟล์ที่จำเป็น
    missing_files = check_required_files()
    status["checks"]["required_files"] = {
        "status": len(missing_files) == 0,
        "missing": missing_files
    }
    
    # ตรวจสอบฟอนต์
    font_count = len([f for f in os.listdir('fonts') 
                     if os.path.splitext(f)[1].lower() in ALLOWED_FONT_EXTENSIONS])
    status["checks"]["fonts"] = {
        "status": font_count > 0,
        "count": font_count
    }
    
    # ตรวจสอบ corpus
    corpus_exists = os.path.exists('corpus/lao_corpus.txt')
    status["checks"]["corpus"] = {
        "status": corpus_exists,
        "exists": corpus_exists
    }
    
    # ตรวจสอบ dataset
    dataset_count = len([f for f in os.listdir('dataset') if f.endswith('.png')])
    status["checks"]["dataset"] = {
        "status": dataset_count > 0,
        "count": dataset_count
    }
    
    # ตรวจสอบ GPU
    try:
        import torch
        gpu_available = torch.cuda.is_available()
        gpu_name = torch.cuda.get_device_name(0) if gpu_available else "N/A"
    except:
        gpu_available = False
        gpu_name = "N/A"
    
    status["checks"]["gpu"] = {
        "status": gpu_available,
        "available": gpu_available,
        "name": gpu_name
    }
    
    # สรุปสถานะ
    status["ready"] = all(check["status"] for check in status["checks"].values() 
                         if "status" in check)
    
    return jsonify(status)

# ⚙️ สร้าง Dataset (ปรับปรุง)
def run_generate_process():
    """รัน subprocess สำหรับสร้าง dataset"""
    log_file = 'logs/dataset_log.txt'
    
    try:
        # เขียน log เริ่มต้น
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({"status": "starting", "message": "กำลังเริ่มต้น..."}, f)
        
        # ตรวจสอบว่ามีไฟล์ script หรือไม่
        script_path = 'training_scripts/generate_dataset.py'
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"ไม่พบไฟล์ {script_path}")
        
        # รัน subprocess
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Dataset generation completed successfully")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Dataset generation failed: {e.stderr}"
        logger.error(error_msg)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({"status": "error", "message": error_msg}, f)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({"status": "error", "message": error_msg}, f)

@app.route('/generate-dataset', methods=['POST'])
def generate_dataset_endpoint():
    # ตรวจสอบความพร้อม
    if not os.path.exists('corpus/lao_corpus.txt'):
        return jsonify({"success": False, "error": "กรุณาอัปโหลด corpus ก่อน"}), 400
    
    font_count = len([f for f in os.listdir('fonts') 
                     if os.path.splitext(f)[1].lower() in ALLOWED_FONT_EXTENSIONS])
    if font_count == 0:
        return jsonify({"success": False, "error": "กรุณาอัปโหลดฟอนต์ก่อน"}), 400
    
    # เริ่มกระบวนการ
    thread = threading.Thread(target=run_generate_process)
    thread.start()
    
    return jsonify({
        "success": True, 
        "message": "เริ่มต้นการสร้างชุดข้อมูลแล้ว",
        "fonts": font_count
    })

# 🟢 สถานะการสร้าง Dataset (ปรับปรุง)
@app.route('/dataset-status')
def dataset_status():
    def generate():
        log_file = 'logs/dataset_log.txt'
        last_data = None
        
        while True:
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        data = f.read()
                    
                    # ส่งข้อมูลเฉพาะเมื่อมีการเปลี่ยนแปลง
                    if data != last_data:
                        yield f"data: {data}\n\n"
                        last_data = data
                    
                    # ตรวจสอบว่าเสร็จแล้วหรือไม่
                    if '"status": "completed"' in data or '"status": "error"' in data:
                        break
                else:
                    yield f"data: {json.dumps({'status': 'waiting'})}\n\n"
                
                time.sleep(0.5)  # ลด delay เพื่อให้ update เร็วขึ้น
                
            except Exception as e:
                logger.error(f"Dataset status error: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                break
    
    return Response(generate(), mimetype='text/event-stream')

# 🤖 เริ่มการฝึกสอน (ปรับปรุง)
def run_training_process(epochs):
    """รัน subprocess สำหรับฝึกสอนโมเดล"""
    log_file = 'logs/training_log.txt'
    
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({"status": "starting", "message": "กำลังเริ่มต้น..."}, f)
        
        script_path = 'training_scripts/train_ocr.py'
        if not os.path.exists(script_path):
            raise FileNotFoundError(f"ไม่พบไฟล์ {script_path}")
        
        # ตรวจสอบว่ามี dataset หรือไม่
        dataset_count = len([f for f in os.listdir('dataset') if f.endswith('.png')])
        if dataset_count == 0:
            raise ValueError("ไม่พบ dataset กรุณาสร้าง dataset ก่อน")
        
        result = subprocess.run(
            [sys.executable, script_path, str(epochs)],
            capture_output=True,
            text=True,
            check=True
        )
        
        logger.info("Training completed successfully")
        
    except subprocess.CalledProcessError as e:
        error_msg = f"Training failed: {e.stderr}"
        logger.error(error_msg)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({"status": "error", "message": error_msg}, f)
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        logger.error(error_msg)
        with open(log_file, 'w', encoding='utf-8') as f:
            json.dump({"status": "error", "message": error_msg}, f)

@app.route('/start-training', methods=['POST'])
def start_training_endpoint():
    try:
        data = request.get_json()
        epochs = int(data.get('epochs', 10))
        
        if epochs < 1 or epochs > 1000:
            return jsonify({"success": False, "error": "จำนวน epochs ต้องอยู่ระหว่าง 1-1000"}), 400
        
        # ตรวจสอบ dataset
        dataset_count = len([f for f in os.listdir('dataset') if f.endswith('.png')])
        if dataset_count == 0:
            return jsonify({"success": False, "error": "ไม่พบ dataset กรุณาสร้าง dataset ก่อน"}), 400
        
        thread = threading.Thread(target=run_training_process, args=(epochs,))
        thread.start()
        
        return jsonify({
            "success": True, 
            "message": "เริ่มต้นกระบวนการฝึกสอนแล้ว",
            "epochs": epochs,
            "dataset_size": dataset_count
        })
        
    except Exception as e:
        logger.error(f"Start training error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 🔁 สถานะ Training (ปรับปรุง) 
@app.route('/training-status')
def training_status():
    def generate():
        log_file = 'logs/training_log.txt'
        last_data = None
        
        while True:
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r', encoding='utf-8') as f:
                        data = f.read()
                    
                    if data != last_data:
                        yield f"data: {data}\n\n"
                        last_data = data
                    
                    if '"status": "completed"' in data or '"status": "error"' in data:
                        break
                else:
                    yield f"data: {json.dumps({'status': 'idle'})}\n\n"
                
                time.sleep(0.5)
                
            except Exception as e:
                logger.error(f"Training status error: {str(e)}")
                yield f"data: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"
                break
    
    return Response(generate(), mimetype='text/event-stream')

# 🖼️ ดูตัวอย่างรูปภาพใน dataset
@app.route('/dataset/preview/<int:page>')
def dataset_preview(page=1):
    """แสดงตัวอย่างรูปภาพใน dataset"""
    try:
        per_page = 20
        image_files = [f for f in os.listdir('dataset') if f.endswith('.png')]
        image_files.sort()
        
        total_images = len(image_files)
        total_pages = (total_images + per_page - 1) // per_page
        
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_images)
        
        images = []
        for i in range(start_idx, end_idx):
            img_name = image_files[i]
            txt_file = img_name.replace('.png', '.gt.txt')
            
            text = ""
            if os.path.exists(os.path.join('dataset', txt_file)):
                with open(os.path.join('dataset', txt_file), 'r', encoding='utf-8') as f:
                    text = f.read().strip()
            
            images.append({
                "filename": img_name,
                "text": text
            })
        
        return jsonify({
            "success": True,
            "images": images,
            "page": page,
            "total_pages": total_pages,
            "total_images": total_images
        })
        
    except Exception as e:
        logger.error(f"Dataset preview error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 🖼️ แสดงรูปภาพ
@app.route('/dataset/image/<filename>')
def dataset_image(filename):
    """แสดงรูปภาพจาก dataset"""
    try:
        return send_from_directory('dataset', filename)
    except Exception as e:
        logger.error(f"Image serving error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 404

# 📥 ดาวน์โหลดโมเดล
@app.route('/models/list')
def list_models():
    """แสดงรายการโมเดลที่ฝึกแล้ว"""
    try:
        models = []
        for filename in os.listdir('models'):
            if filename.endswith('.pth'):
                filepath = os.path.join('models', filename)
                file_size = os.path.getsize(filepath)
                file_time = os.path.getmtime(filepath)
                
                models.append({
                    "filename": filename,
                    "size": f"{file_size / 1024 / 1024:.2f} MB",
                    "created": time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(file_time))
                })
        
        models.sort(key=lambda x: x["created"], reverse=True)
        
        return jsonify({
            "success": True,
            "models": models
        })
        
    except Exception as e:
        logger.error(f"List models error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/models/download/<filename>')
def download_model(filename):
    """ดาวน์โหลดไฟล์โมเดล"""
    try:
        return send_file(
            os.path.join('models', filename),
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        logger.error(f"Model download error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 404

# 🧹 ลบข้อมูล
@app.route('/clear/<data_type>', methods=['POST'])
def clear_data(data_type):
    """ลบข้อมูลตามประเภท"""
    try:
        if data_type == 'dataset':
            for f in os.listdir('dataset'):
                os.remove(os.path.join('dataset', f))
            message = "ลบ dataset ทั้งหมดแล้ว"
        elif data_type == 'models':
            for f in os.listdir('models'):
                if f.endswith('.pth'):
                    os.remove(os.path.join('models', f))
            message = "ลบโมเดลทั้งหมดแล้ว"
        elif data_type == 'fonts':
            for f in os.listdir('fonts'):
                if os.path.splitext(f)[1].lower() in ALLOWED_FONT_EXTENSIONS:
                    os.remove(os.path.join('fonts', f))
            message = "ลบฟอนต์ทั้งหมดแล้ว"
        else:
            return jsonify({"success": False, "error": "ประเภทข้อมูลไม่ถูกต้อง"}), 400
        
        logger.info(f"Cleared {data_type}")
        return jsonify({"success": True, "message": message})
        
    except Exception as e:
        logger.error(f"Clear data error: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

# 🚀 เริ่ม Flask App
if __name__ == '__main__':
    # ตรวจสอบความพร้อมก่อนเริ่ม
    missing_files = check_required_files()
    if missing_files:
        logger.warning("=== คำเตือน: ไฟล์ที่จำเป็นยังไม่ครบ ===")
        for file in missing_files:
            logger.warning(f"- {file}")
        logger.warning("กรุณาตรวจสอบให้แน่ใจว่ามีไฟล์ครบถ้วน")
    
    # สร้างไฟล์ log เริ่มต้น
    os.makedirs('logs', exist_ok=True)
    for log_file in ['logs/dataset_log.txt', 'logs/training_log.txt']:
        if not os.path.exists(log_file):
            with open(log_file, 'w', encoding='utf-8') as f:
                json.dump({"status": "idle"}, f)
    
    app.run(debug=True, threaded=True, host='0.0.0.0', port=5000)