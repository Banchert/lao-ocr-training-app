# training_scripts/generate_dataset.py (ฉบับปรับปรุงใหม่ มีประสิทธิภาพและเสถียร)
import os
import sys
import random
import json
import time
import multiprocessing
from PIL import Image, ImageDraw, ImageFont

# ==============================================================================
# === การตั้งค่าหลัก (สามารถปรับแก้ได้จากตรงนี้) ===
# ==============================================================================
# ตั้งค่า Path หลัก
BASE_DIR = os.path.dirname(os.path.dirname(__file__))
FONT_DIR = os.path.join(BASE_DIR, 'fonts')
CORPUS_FILE = os.path.join(BASE_DIR, 'corpus', 'lao_corpus.txt')
OUTPUT_DIR = os.path.join(BASE_DIR, 'dataset')
LOG_FILE = os.path.join(BASE_DIR, 'logs', 'dataset_log.txt')

# การตั้งค่าการสร้างภาพ
NUM_IMAGES_PER_FONT = 200  # จำนวนรูปภาพที่จะสร้างต่อ 1 ฟอนต์
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 100
FONT_SIZE = 32

# การตั้งค่าประสิทธิภาพ
# ใช้จำนวน CPU Core ทั้งหมดที่มี ลบไป 1 เพื่อให้เครื่องยังตอบสนองได้
CPU_WORKERS = max(1, multiprocessing.cpu_count() - 1)


# ==============================================================================
# === ฟังก์ชันช่วยเหลือ (Utility Functions) ===
# ==============================================================================
def write_log(log_data):
    """เขียน log file ด้วย UTF-8 encoding เพื่อให้หน้าเว็บนำไปใช้"""
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)

def is_lao_font(font_object):
    """
    ตรวจสอบว่าฟอนต์รองรับภาษาลาวหรือไม่ โดยทดสอบการแสดงผลตัวอักษรลาว
    (ใช้ฟังก์ชันเดิมจากไฟล์เก่า)
    """
    test_chars = ['ກ', 'ຂ', 'ຄ', 'ງ', 'ຈ', 'ເ', 'ແ', 'ໂ', 'ໃ', 'ໄ', '່', '້']
    try:
        # ทดสอบว่าตัวอักษรแต่ละตัวมีขนาด (width) หรือไม่
        char_widths = [font_object.getbbox(char)[2] for char in test_chars]
        # หากฟอนต์ไม่รองรับเลย ขนาดมักจะเป็น 0 หรือเท่ากันหมด
        if sum(char_widths) < len(test_chars) * 5 or len(set(char_widths)) < 3:
            return False
        
        # ทดสอบการวาดข้อความจริง
        test_text = "ສະບາຍດີ"
        bbox = font_object.getbbox(test_text)
        return (bbox[2] - bbox[0]) > 20 # ข้อความควรมีความกว้างพอสมควร
    except Exception:
        return False

# ==============================================================================
# === ฟังก์ชันสำหรับ Worker Process (ประมวลผลแบบขนาน) ===
# ==============================================================================
def create_single_image(task_args):
    """
    ฟังก์ชันที่ถูกเรียกโดย Worker แต่ละตัวเพื่อสร้างรูปภาพ 1 รูป
    รับ arguments ทั้งหมดมาใน tuple เดียวเพื่อความง่ายในการส่งงาน
    """
    font_path, text_to_render, output_filename_base = task_args
    
    try:
        font = ImageFont.truetype(font_path, FONT_SIZE)
        
        # สร้างรูปภาพ
        image = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), 'white')
        draw = ImageDraw.Draw(image)

        # คำนวณตำแหน่งและวาดข้อความ
        bbox = draw.textbbox((0, 0), text_to_render, font=font)
        text_height = bbox[3] - bbox[1]
        position = (10, (IMAGE_HEIGHT - text_height) // 2)
        draw.text(position, text_to_render, fill='black', font=font)

        # บันทึกไฟล์รูปภาพและไฟล์ข้อความ (Ground Truth)
        png_path = f"{output_filename_base}.png"
        gt_txt_path = f"{output_filename_base}.gt.txt"
        
        image.save(png_path)
        with open(gt_txt_path, 'w', encoding='utf-8') as f:
            f.write(text_to_render)
            
        return "success"
    except Exception as e:
        # หากเกิดข้อผิดพลาดกับรูปภาพใดภาพหนึ่ง ให้ส่งคืนเป็น error แทนที่จะทำให้โปรแกรมหยุด
        print(f"Error processing {os.path.basename(font_path)}: {e}", file=sys.stderr)
        return "error"

# ==============================================================================
# === ฟังก์ชันหลักในการควบคุมการทำงาน ===
# ==============================================================================
def run_generation():
    """
    ฟังก์ชันหลักที่ควบคุมกระบวนการทั้งหมด: ตรวจสอบฟอนต์, เตรียมงาน, และสั่งประมวลผลแบบขนาน
    """
    start_time = time.time()
    
    # --- 1. ตรวจสอบไฟล์และโฟลเดอร์ที่จำเป็น ---
    print("Step 1: Checking prerequisites...")
    write_log({"status": "starting", "message": "ตรวจสอบไฟล์และโฟลเดอร์..."})
    
    if not os.path.exists(CORPUS_FILE):
        write_log({"status": "error", "message": "ไม่พบไฟล์ Corpus (lao_corpus.txt)"})
        return
        
    with open(CORPUS_FILE, 'r', encoding='utf-8') as f:
        corpus = [line.strip() for line in f if line.strip()]
    if not corpus:
        write_log({"status": "error", "message": "ไฟล์ Corpus ว่างเปล่า กรุณาใส่ข้อมูล"})
        return

    all_font_files = [f for f in os.listdir(FONT_DIR) if f.lower().endswith(('.ttf', '.otf'))]
    if not all_font_files:
        write_log({"status": "error", "message": "ไม่พบไฟล์ฟอนต์ในโฟลเดอร์ fonts"})
        return

    # --- 2. คัดกรองฟอนต์ที่รองรับภาษาลาว ---
    print("Step 2: Validating Lao fonts...")
    write_log({"status": "filtering", "message": "กำลังคัดกรองฟอนต์ที่รองรับภาษาลาว..."})
    
    valid_fonts = []
    invalid_fonts = []
    for font_name in all_font_files:
        font_path = os.path.join(FONT_DIR, font_name)
        try:
            font_obj = ImageFont.truetype(font_path, FONT_SIZE)
            if is_lao_font(font_obj):
                valid_fonts.append(font_path)
                print(f"  ✅  Valid: {font_name}")
            else:
                invalid_fonts.append(font_name)
                print(f"  ❌  Invalid (Not a Lao font): {font_name}")
        except Exception as e:
            invalid_fonts.append(font_name)
            print(f"  ⚠️  Error loading {font_name}: {e}")
            
    if not valid_fonts:
        write_log({"status": "error", "message": f"ไม่พบฟอนต์ที่รองรับภาษาลาว! (ฟอนต์ที่พบ {len(invalid_fonts)} ไฟล์ไม่รองรับ)"})
        return

    # --- 3. เตรียม "รายการงาน" (Tasks) ทั้งหมด ---
    print(f"\nStep 3: Preparing {len(valid_fonts) * NUM_IMAGES_PER_FONT} tasks for generation...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    tasks = []
    for font_path in valid_fonts:
        font_basename = os.path.splitext(os.path.basename(font_path))[0].replace(" ", "_")
        for i in range(NUM_IMAGES_PER_FONT):
            text_to_render = random.choice(corpus)
            output_base = os.path.join(OUTPUT_DIR, f"lao_{font_basename}_{i:04d}")
            tasks.append((font_path, text_to_render, output_base))

    total_tasks = len(tasks)
    
    # --- 4. เริ่มการประมวลผลแบบขนาน (Multiprocessing) ---
    print(f"\nStep 4: Starting generation with {CPU_WORKERS} CPU workers...")
    
    processed_count = 0
    success_count = 0
    error_count = 0

    with multiprocessing.Pool(processes=CPU_WORKERS) as pool:
        # ใช้ imap_unordered เพื่อให้ได้ผลลัพธ์กลับมาทันทีที่งานเสร็จ ไม่ต้องรอตามลำดับ
        for result in pool.imap_unordered(create_single_image, tasks):
            processed_count += 1
            if result == "success":
                success_count += 1
            else:
                error_count += 1

            # อัปเดต Log ทุกๆ 1% หรือทุก 50 งาน เพื่อให้ UI ตอบสนอง
            if processed_count % (total_tasks // 100 or 1) == 0 or processed_count % 50 == 0:
                progress = int((processed_count / total_tasks) * 100)
                elapsed_time = time.time() - start_time
                est_remaining = (elapsed_time / processed_count) * (total_tasks - processed_count) if processed_count > 0 else 0

                status = {
                    "status": "generating",
                    "message": f"ประมวลผล... เหลือเวลาประมาณ {int(est_remaining)} วินาที",
                    "progress": progress,
                    "detail": f"สร้างแล้ว {success_count}/{total_tasks} (ล้มเหลว {error_count})",
                }
                write_log(status)

    # --- 5. สรุปผลการทำงาน ---
    print("\nStep 5: Generation complete.")
    total_time = time.time() - start_time
    final_status = {
        "status": "completed",
        "message": f"สร้างชุดข้อมูลเสร็จสิ้นใน {total_time:.2f} วินาที!",
        "progress": 100,
        "summary": {
            "total_images_created": success_count,
            "failed_images": error_count,
            "fonts_used": len(valid_fonts),
            "skipped_fonts": len(invalid_fonts),
            "output_directory": OUTPUT_DIR,
        }
    }
    write_log(final_status)
    print(json.dumps(final_status, indent=4, ensure_ascii=False))


if __name__ == '__main__':
    # ตั้งค่า encoding สำหรับ Windows โดยเฉพาะ
    if sys.platform == 'win32':
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')

    try:
        run_generation()
    except Exception as e:
        # ดักจับข้อผิดพลาดที่ไม่คาดคิดในระดับบนสุด
        print(f"FATAL ERROR: {e}", file=sys.stderr)
        write_log({"status": "error", "message": f"เกิดข้อผิดพลาดร้ายแรง: {e}"})
        sys.exit(1)