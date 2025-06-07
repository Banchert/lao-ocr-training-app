# test_fonts.py - ทดสอบฟอนต์ที่อัปโหลด
import os
import sys
from PIL import Image, ImageDraw, ImageFont

# ตั้งค่า encoding สำหรับ Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

def test_all_fonts():
    """ทดสอบฟอนต์ทั้งหมดในโฟลเดอร์ fonts"""
    fonts_dir = 'fonts'
    output_dir = 'font_tests'
    
    # สร้างโฟลเดอร์สำหรับเก็บผลทดสอบ
    os.makedirs(output_dir, exist_ok=True)
    
    # ข้อความทดสอบ
    test_text = """ທົດສອບພາສາລາວ
ສະບາຍດີ ຂອບໃຈຫຼາຍໆ
ABCDEFG 1234567890
Mixed: ລາວ Lao 123"""
    
    font_files = [f for f in os.listdir(fonts_dir) if f.endswith(('.ttf', '.otf'))]
    
    print(f"พบฟอนต์ทั้งหมด {len(font_files)} ไฟล์\n")
    
    results = []
    
    for font_file in font_files:
        font_path = os.path.join(fonts_dir, font_file)
        output_path = os.path.join(output_dir, f"test_{font_file}.png")
        
        print(f"ทดสอบ: {font_file}")
        
        try:
            # โหลดฟอนต์
            font = ImageFont.truetype(font_path, 40)
            
            # สร้างรูปภาพ
            img = Image.new('RGB', (800, 300), 'white')
            draw = ImageDraw.Draw(img)
            
            # เขียนชื่อฟอนต์
            draw.text((10, 10), f"Font: {font_file}", font=font, fill='blue')
            
            # เขียนข้อความทดสอบ
            y_pos = 60
            for line in test_text.split('\n'):
                draw.text((10, y_pos), line, font=font, fill='black')
                y_pos += 50
            
            # บันทึกรูปภาพ
            img.save(output_path)
            
            # ตรวจสอบว่าแสดงภาษาลาวได้หรือไม่
            # (ตรวจสอบแบบง่ายๆ โดยดูขนาดของข้อความ)
            bbox = draw.textbbox((0, 0), "ສະບາຍດີ", font=font)
            text_width = bbox[2] - bbox[0]
            
            if text_width > 50:  # ถ้าข้อความมีความกว้างพอสมควร
                print(f"  ✅ รองรับภาษาลาว (ความกว้างข้อความ: {text_width}px)")
                results.append((font_file, True))
            else:
                print(f"  ❌ ไม่รองรับภาษาลาว (ความกว้างข้อความ: {text_width}px)")
                results.append((font_file, False))
                
        except Exception as e:
            print(f"  ⚠️ เกิดข้อผิดพลาด: {e}")
            results.append((font_file, False))
        
        print()
    
    # สรุปผล
    print("\n" + "="*50)
    print("สรุปผลการทดสอบ:")
    print("="*50)
    
    lao_fonts = [f for f, supported in results if supported]
    non_lao_fonts = [f for f, supported in results if not supported]
    
    print(f"\n✅ ฟอนต์ที่รองรับภาษาลาว ({len(lao_fonts)} ฟอนต์):")
    for font in lao_fonts:
        print(f"   - {font}")
    
    print(f"\n❌ ฟอนต์ที่ไม่รองรับภาษาลาว ({len(non_lao_fonts)} ฟอนต์):")
    for font in non_lao_fonts:
        print(f"   - {font}")
    
    print(f"\nผลการทดสอบถูกบันทึกไว้ในโฟลเดอร์: {output_dir}")
    
    # สร้างไฟล์สรุป
    summary_path = os.path.join(output_dir, "summary.txt")
    with open(summary_path, 'w', encoding='utf-8') as f:
        f.write("สรุปผลการทดสอบฟอนต์\n")
        f.write("="*50 + "\n\n")
        f.write(f"ฟอนต์ที่รองรับภาษาลาว ({len(lao_fonts)} ฟอนต์):\n")
        for font in lao_fonts:
            f.write(f"- {font}\n")
        f.write(f"\nฟอนต์ที่ไม่รองรับภาษาลาว ({len(non_lao_fonts)} ฟอนต์):\n")
        for font in non_lao_fonts:
            f.write(f"- {font}\n")

if __name__ == "__main__":
    test_all_fonts()