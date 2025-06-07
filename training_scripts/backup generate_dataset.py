# training_scripts/generate_dataset.py (ฉบับปรับปรุงการตรวจสอบฟอนต์)
import os
import sys
import random
from PIL import Image, ImageDraw, ImageFont
import json
import time

# ตั้งค่า encoding สำหรับ Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# --- เพิ่มฟังก์ชันสำหรับเขียน Log ---
def write_dataset_log(log_data):
    """เขียน log file ด้วย UTF-8 encoding"""
    log_path = os.path.join(os.path.dirname(__file__), '..', 'logs', 'dataset_log.txt')
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)

# ==============================================================================
# === ฟังก์ชันตรวจสอบฟอนต์ลาวแบบละเอียด (ฉบับปรับปรุง) ===
# ==============================================================================
def is_lao_font(font_object):
    """
    ตรวจสอบว่าฟอนต์รองรับภาษาลาวหรือไม่
    โดยทดสอบการแสดงผลตัวอักษรลาวหลายตัว
    """
    # ตัวอักษรลาวที่ต้องทดสอบ (ครอบคลุมทุกประเภท)
    test_chars = [
        'ກ', 'ຂ', 'ຄ', 'ງ', 'ຈ',  # พยัญชนะ
        'ເ', 'ແ', 'ໂ', 'ໃ', 'ໄ',  # สระ
        'ໜ', 'ໝ',                  # พยัญชนะควบ
        '່', '້', '໊', '໋',         # วรรณยุกต์
        'ໆ', 'ຯ'                   # เครื่องหมายพิเศษ
    ]
    
    # ตัวอักษรที่ไม่ควรแสดงผล (ใช้ตรวจสอบว่าฟอนต์ไม่ได้แสดงทุกอย่างเหมือนกัน)
    non_lao_chars = ['Ω', '∆', '√']  # ตัวอักษรพิเศษที่ไม่น่าจะมีในฟอนต์ลาว
    
    try:
        # สร้างรูปภาพทดสอบ
        test_img = Image.new('RGB', (200, 50), 'white')
        draw = ImageDraw.Draw(test_img)
        
        # ทดสอบตัวอักษรลาว
        lao_sizes = []
        for char in test_chars:
            try:
                bbox = draw.textbbox((0, 0), char, font=font_object)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                
                # ถ้าขนาดเป็น 0 หรือเล็กเกินไป แสดงว่าไม่รองรับ
                if width <= 2 or height <= 2:
                    return False
                    
                lao_sizes.append((width, height))
            except:
                # ถ้าเกิด error แสดงว่าไม่รองรับ
                return False
        
        # ทดสอบตัวอักษรที่ไม่ควรมี
        non_lao_sizes = []
        for char in non_lao_chars:
            try:
                bbox = draw.textbbox((0, 0), char, font=font_object)
                width = bbox[2] - bbox[0]
                height = bbox[3] - bbox[1]
                non_lao_sizes.append((width, height))
            except:
                pass
        
        # ตรวจสอบว่าตัวอักษรลาวมีขนาดที่แตกต่างกัน (ไม่ใช่แค่กล่องเดียวกัน)
        unique_sizes = len(set(lao_sizes))
        if unique_sizes < 3:  # ควรมีขนาดที่แตกต่างกันอย่างน้อย 3 แบบ
            return False
        
        # ตรวจสอบว่าตัวอักษรลาวและไม่ใช่ลาวมีขนาดต่างกัน
        if non_lao_sizes:
            avg_lao_width = sum(s[0] for s in lao_sizes) / len(lao_sizes)
            avg_non_lao_width = sum(s[0] for s in non_lao_sizes) / len(non_lao_sizes)
            
            # ถ้าขนาดเฉลี่ยเหมือนกันมาก แสดงว่าฟอนต์อาจแสดงทุกอย่างเป็นกล่องเดียวกัน
            if abs(avg_lao_width - avg_non_lao_width) < 2:
                return False
        
        # ทดสอบการแสดงผลข้อความจริง
        test_text = "ສະບາຍດີ"  # "สบายดี" ในภาษาลาว
        try:
            bbox = draw.textbbox((0, 0), test_text, font=font_object)
            text_width = bbox[2] - bbox[0]
            
            # ข้อความควรมีความกว้างพอสมควร
            if text_width < 20:
                return False
                
        except:
            return False
        
        return True
        
    except Exception as e:
        print(f"Error in font validation: {e}")
        return False

def test_font_completeness(font_object, sample_text):
    """
    ทดสอบว่าฟอนต์สามารถแสดงข้อความที่กำหนดได้ครบถ้วนหรือไม่
    """
    try:
        # สร้างรูปภาพทดสอบ
        test_img = Image.new('RGB', (800, 100), 'white')
        draw = ImageDraw.Draw(test_img)
        
        # วาดข้อความ
        draw.text((10, 10), sample_text, font=font_object, fill='black')
        
        # แปลงเป็น pixel data
        pixels = test_img.load()
        
        # นับจำนวน pixel ที่ไม่ใช่สีขาว
        non_white_pixels = 0
        for x in range(test_img.width):
            for y in range(test_img.height):
                if pixels[x, y] != (255, 255, 255):
                    non_white_pixels += 1
        
        # ถ้ามี pixel ที่ไม่ใช่สีขาวน้อยเกินไป แสดงว่าอาจแสดงเป็นกล่อง
        # (ค่านี้อาจต้องปรับตามขนาดฟอนต์)
        min_expected_pixels = len(sample_text) * 50  # ประมาณ 50 pixels ต่อตัวอักษร
        
        return non_white_pixels > min_expected_pixels
        
    except Exception as e:
        print(f"Error testing font completeness: {e}")
        return False

# ==============================================================================
# === ค่าที่สามารถปรับได้ ===
# ==============================================================================
FONT_DIR = os.path.join(os.path.dirname(__file__), '..', 'fonts')
CORPUS_FILE = os.path.join(os.path.dirname(__file__), '..', 'corpus', 'lao_corpus.txt')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), '..', 'dataset')
NUM_IMAGES_PER_FONT = 200
IMAGE_WIDTH = 800
IMAGE_HEIGHT = 100
FONT_SIZE = 32

# สร้างโฟลเดอร์สำหรับเก็บรูปทดสอบฟอนต์
FONT_TEST_DIR = os.path.join(os.path.dirname(__file__), '..', 'font_tests')
os.makedirs(FONT_TEST_DIR, exist_ok=True)

def save_font_test_image(font_name, font_object, is_valid):
    """บันทึกรูปทดสอบฟอนต์"""
    try:
        img = Image.new('RGB', (800, 200), 'white')
        draw = ImageDraw.Draw(img)
        
        # ข้อความทดสอบ
        test_texts = [
            f"Font: {font_name} - {'✅ VALID' if is_valid else '❌ INVALID'}",
            "English: ABCDEFG abcdefg 123456",
            "ພາສາລາວ: ສະບາຍດີ ຂອບໃຈ",
            "ປະສົມ Mixed: Lao ລາວ 123"
        ]
        
        y_pos = 10
        for text in test_texts:
            try:
                draw.text((10, y_pos), text, font=font_object, fill='black' if is_valid else 'red')
            except:
                draw.text((10, y_pos), f"[Error rendering: {text[:20]}...]", fill='red')
            y_pos += 45
        
        # บันทึกรูปภาพ
        output_path = os.path.join(FONT_TEST_DIR, f"test_{font_name}.png")
        img.save(output_path)
        
    except Exception as e:
        print(f"Error saving font test image: {e}")

def load_corpus(filename):
    """โหลดไฟล์ corpus พร้อมจัดการ encoding"""
    print(f"Loading corpus from: {filename}")
    try:
        if not os.path.exists(filename):
            print(f"Corpus file not found: {filename}")
            return []
        
        with open(filename, 'r', encoding='utf-8') as f:
            lines = [line.strip() for line in f if line.strip()]
        
        print(f"Loaded {len(lines)} lines from corpus")
        return lines
    except Exception as e:
        print(f"Error loading corpus: {e}")
        return []

def generate_dataset():
    """ฟังก์ชันหลักสำหรับสร้าง dataset"""
    # สร้างโฟลเดอร์ output
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # โหลด corpus
    corpus = load_corpus(CORPUS_FILE)
    if not corpus:
        error_msg = "No corpus data found. Please upload a corpus file first."
        print(error_msg)
        write_dataset_log({"status": "error", "message": error_msg})
        return

    # ตรวจสอบฟอนต์
    if not os.path.exists(FONT_DIR):
        error_msg = f"Font directory not found: {FONT_DIR}"
        print(error_msg)
        write_dataset_log({"status": "error", "message": error_msg})
        return

    all_font_files = [f for f in os.listdir(FONT_DIR) if f.endswith(('.ttf', '.otf'))]
    if not all_font_files:
        error_msg = "No font files found in fonts directory"
        print(error_msg)
        write_dataset_log({"status": "error", "message": error_msg})
        return
    
    # คัดกรองฟอนต์ลาว
    lao_fonts = []
    invalid_fonts = []
    
    print("="*60)
    print("Starting font validation...")
    print("="*60)
    write_dataset_log({"status": "filtering", "message": "Validating fonts..."})
    
    for i, font_name in enumerate(all_font_files):
        font_path = os.path.join(FONT_DIR, font_name)
        print(f"\n[{i+1}/{len(all_font_files)}] Testing: {font_name}")
        
        try:
            temp_font = ImageFont.truetype(font_path, FONT_SIZE)
            
            # ทดสอบว่าเป็นฟอนต์ลาวหรือไม่
            if is_lao_font(temp_font):
                # ทดสอบเพิ่มเติมด้วยข้อความจาก corpus
                sample_text = random.choice(corpus) if corpus else "ສະບາຍດີ ລາວ"
                if test_font_completeness(temp_font, sample_text):
                    lao_fonts.append(font_name)
                    print(f"  ✅ Valid Lao font")
                    save_font_test_image(os.path.splitext(font_name)[0], temp_font, True)
                else:
                    invalid_fonts.append((font_name, "Incomplete character set"))
                    print(f"  ⚠️ Lao font but incomplete character set")
                    save_font_test_image(os.path.splitext(font_name)[0], temp_font, False)
            else:
                invalid_fonts.append((font_name, "Not a Lao font"))
                print(f"  ❌ Not a Lao font")
                save_font_test_image(os.path.splitext(font_name)[0], temp_font, False)
                
        except Exception as e:
            invalid_fonts.append((font_name, f"Error: {str(e)}"))
            print(f"  ❌ Error loading font: {e}")
            continue
    
    # แสดงสรุปผล
    print("\n" + "="*60)
    print("FONT VALIDATION SUMMARY")
    print("="*60)
    print(f"Total fonts tested: {len(all_font_files)}")
    print(f"Valid Lao fonts: {len(lao_fonts)}")
    print(f"Invalid/Skipped fonts: {len(invalid_fonts)}")
    
    if invalid_fonts:
        print("\nSkipped fonts:")
        for font, reason in invalid_fonts:
            print(f"  - {font}: {reason}")
    
    print(f"\nFont test images saved to: {FONT_TEST_DIR}")
    print("="*60)
    
    if not lao_fonts:
        error_msg = "No valid Lao fonts found! Please upload proper Lao fonts."
        print(f"\n{error_msg}")
        write_dataset_log({"status": "error", "message": error_msg})
        return

    print(f"\nStarting dataset generation with {len(lao_fonts)} valid fonts...")
    
    total_fonts = len(lao_fonts)
    total_images_to_create = total_fonts * NUM_IMAGES_PER_FONT
    images_created = 0
    failed_images = 0

    for font_idx, font_name in enumerate(lao_fonts):
        font_path = os.path.join(FONT_DIR, font_name)
        font_basename = os.path.splitext(font_name)[0].replace(" ", "_")

        try:
            font = ImageFont.truetype(font_path, FONT_SIZE)
        except IOError:
            print(f"Cannot load font: {font_name}")
            continue

        print(f"\nProcessing font {font_idx+1}/{total_fonts}: {font_name}")

        for i in range(NUM_IMAGES_PER_FONT):
            try:
                images_created += 1
                
                # Update progress
                if images_created % 5 == 0:
                    progress = int((images_created / total_images_to_create) * 100)
                    status = {
                        "status": "generating", 
                        "message": f"Processing font {font_idx+1}/{total_fonts}: {font_name}",
                        "progress": progress, 
                        "detail": f"Created {images_created}/{total_images_to_create} images"
                    }
                    write_dataset_log(status)
                
                # สุ่มเลือกข้อความ
                text_to_render = random.choice(corpus)
                
                # สร้างชื่อไฟล์
                image_filename = f"lao_{font_basename}_{i:04d}"
                
                # สร้างรูปภาพ
                image = Image.new('RGB', (IMAGE_WIDTH, IMAGE_HEIGHT), 'white')
                draw = ImageDraw.Draw(image)
                
                # คำนวณตำแหน่งข้อความ
                bbox = draw.textbbox((0, 0), text_to_render, font=font)
                text_width = bbox[2] - bbox[0]
                text_height = bbox[3] - bbox[1]
                
                position = (10, (IMAGE_HEIGHT - text_height) // 2)
                
                # วาดข้อความ
                draw.text(position, text_to_render, fill='black', font=font)
                
                # ตรวจสอบว่ามีการวาดข้อความจริงๆ (ไม่ใช่แค่กล่อง)
                # โดยตรวจสอบว่ามี pixel สีดำพอสมควร
                pixels = image.load()
                black_pixels = sum(1 for x in range(image.width) for y in range(image.height) 
                                 if pixels[x, y] != (255, 255, 255))
                
                if black_pixels < 100:  # ถ้ามี pixel สีดำน้อยเกินไป
                    failed_images += 1
                    continue
                
                # บันทึกไฟล์
                png_path = os.path.join(OUTPUT_DIR, f"{image_filename}.png")
                gt_txt_path = os.path.join(OUTPUT_DIR, f"{image_filename}.gt.txt")
                
                image.save(png_path)
                
                # บันทึก ground truth text
                with open(gt_txt_path, 'w', encoding='utf-8') as f:
                    f.write(text_to_render)
                    
            except Exception as e:
                print(f"  Error creating image {i}: {e}")
                failed_images += 1
                continue

    # สร้างสรุป
    actual_images_created = images_created - failed_images
    final_status = {
        "status": "completed", 
        "message": "Dataset generation completed!", 
        "progress": 100,
        "summary": {
            "total_images_created": actual_images_created,
            "failed_images": failed_images,
            "fonts_used": len(lao_fonts),
            "skipped_fonts": len(invalid_fonts),
            "output_directory": OUTPUT_DIR
        }
    }
    write_dataset_log(final_status)
    
    print("\n" + "="*60)
    print("DATASET GENERATION COMPLETED")
    print("="*60)
    print(f"Successfully created: {actual_images_created} images")
    print(f"Failed: {failed_images} images")
    print(f"Fonts used: {len(lao_fonts)}")
    print(f"Output directory: {OUTPUT_DIR}")
    print("="*60)

if __name__ == '__main__':
    try:
        generate_dataset()
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)}"
        print(error_msg)
        write_dataset_log({"status": "error", "message": error_msg})
        sys.exit(1)