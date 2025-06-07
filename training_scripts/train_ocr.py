# training_scripts/train_ocr.py
# เวอร์ชันแก้ไข encoding error สำหรับ Windows

import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
import torchvision.transforms as transforms
from PIL import Image
import time
import json
import sys
import os

# ตั้งค่า encoding สำหรับ Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ==============================================================================
# 1. คลาสสำหรับจัดการ Dataset ของเราโดยเฉพาะ
# ==============================================================================
class LaoOCRDataset(Dataset):
    """Custom Dataset สำหรับโหลดรูปภาพและข้อความภาษาลาวของเรา"""
    def __init__(self, dataset_dir, transform=None):
        self.dataset_dir = dataset_dir
        self.transform = transform
        self.image_files = [f for f in os.listdir(dataset_dir) if f.endswith('.png')]
        
        # สร้าง mapping สำหรับตัวอักษรทั้งหมด
        all_chars = "ກຂຄງຈສຊຍດຕຖທນບປຜຝພຟມຢຣລວຫອຮເແໂໃໄໆໜໝ" + \
                    "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ .,()-"
        self.char_to_idx = {char: i + 1 for i, char in enumerate(all_chars)}
        self.idx_to_char = {i + 1: char for i, char in enumerate(all_chars)}
        # +1 สำหรับ blank token ที่ใช้ในอัลกอริทึมบางประเภทเช่น CTCLoss
        self.vocab_size = len(all_chars) + 1 

    def __len__(self):
        return len(self.image_files)

    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        img_path = os.path.join(self.dataset_dir, img_name)
        
        try:
            # โหลดรูปภาพ
            image = Image.open(img_path).convert('L')  # แปลงเป็น Grayscale
            
            # โหลดข้อความ
            txt_path = os.path.join(self.dataset_dir, os.path.splitext(img_name)[0] + '.gt.txt')
            with open(txt_path, 'r', encoding='utf-8') as f:
                label_text = f.read().strip()
            
            # แปลงข้อความเป็นตัวเลข
            label_indices = [self.char_to_idx.get(char, 0) for char in label_text] # 0 for unknown
            
            if self.transform:
                image = self.transform(image)
                
            return image, torch.LongTensor(label_indices)
        except Exception as e:
            print(f"Error loading data: {img_path} - {e}")
            # ส่งคืนข้อมูลเปล่าถ้าไฟล์มีปัญหา
            return torch.zeros(1, 64, 400), torch.LongTensor([0])


# ==============================================================================
# 2. ฟังก์ชันสำหรับเขียน Log ไปยังหน้าเว็บ
# ==============================================================================
def write_log(log_data, log_file):
    """ฟังก์ชันสำหรับเขียน log อย่างปลอดภัย"""
    full_path = os.path.join(os.path.dirname(__file__), '..', 'logs', log_file)
    os.makedirs(os.path.dirname(full_path), exist_ok=True)
    with open(full_path, 'w', encoding='utf-8') as f:
        json.dump(log_data, f, ensure_ascii=False, indent=4)


# ==============================================================================
# 3. ฟังก์ชันหลักสำหรับการฝึกสอน
# ==============================================================================
def train_on_gpu(total_epochs, log_file="training_log.txt"):
    """ฟังก์ชันสำหรับฝึกสอนโมเดลบน GPU ด้วยข้อมูลจริง"""
    
    # --- ส่วนที่ 1: การตั้งค่าพื้นฐาน ---
    if torch.cuda.is_available():
        device = torch.device("cuda")
        device_name = torch.cuda.get_device_name(0)
        print(f"Found GPU: {device_name}. Starting training on GPU...")
        write_log({"status": "initializing", "message": f"Initializing on {device_name}"}, log_file)
    else:
        device = torch.device("cpu")
        print("No GPU found, using CPU (much slower)")
        write_log({"status": "initializing", "message": "No GPU found, using CPU"}, log_file)
    
    time.sleep(1)

    # --- ส่วนที่ 2: การโหลด Dataset จริง ---
    print("Loading real dataset from 'dataset/' directory...")
    
    transform = transforms.Compose([
        transforms.Resize((64, 400)),
        transforms.ToTensor(),
        transforms.Normalize((0.5,), (0.5,))
    ])

    # ใช้ path แบบ relative ที่ถูกต้อง
    dataset_path = os.path.join(os.path.dirname(__file__), '..', 'dataset')
    real_dataset = LaoOCRDataset(dataset_dir=dataset_path, transform=transform)
    
    if len(real_dataset) == 0:
        error_msg = "No data found in dataset folder! Please generate dataset first."
        print(error_msg)
        write_log({"status": "error", "message": error_msg}, log_file)
        return

    print(f"Dataset loaded successfully! Found {len(real_dataset)} images")

    batch_size = 32
    train_loader = DataLoader(real_dataset, batch_size=batch_size, shuffle=True, num_workers=0, pin_memory=True)

    # --- ส่วนที่ 3: การสร้างโมเดล ---
    # หมายเหตุ: นี่คือโมเดลอย่างง่ายสำหรับทดสอบการทำงานเท่านั้น
    # สำหรับงาน OCR จริง ควรใช้สถาปัตยกรรมที่ซับซ้อนกว่านี้ เช่น CRNN (CNN + RNN)
    model = nn.Sequential(
        nn.Conv2d(1, 16, kernel_size=3, stride=1, padding=1), nn.ReLU(), nn.MaxPool2d(2, 2),
        nn.Conv2d(16, 32, kernel_size=3, stride=1, padding=1), nn.ReLU(), nn.MaxPool2d(2, 2),
        nn.Flatten(),
        nn.Linear(32 * 16 * 100, real_dataset.vocab_size) # **ปรับ Output ให้เท่ากับจำนวนคำศัพท์**
    ).to(device)
    
    # Loss Function ที่เหมาะกับ OCR คือ CTCLoss แต่เพื่อความง่ายจะใช้ CrossEntropy ไปก่อน
    optimizer = torch.optim.Adam(model.parameters(), lr=0.001)
    criterion = nn.CrossEntropyLoss()

    # --- ส่วนที่ 4: Training Loop ---
    total_steps = len(train_loader)
    print(f"Starting training for {total_epochs} epochs...")
    
    for epoch in range(1, total_epochs + 1):
        epoch_loss = 0
        epoch_start_time = time.time()
        
        for i, (images, labels) in enumerate(train_loader):
            images, labels = images.to(device), labels.to(device)
            
            # ในงานจริง labels จะต้องถูกจัดรูปแบบให้เหมาะกับ Loss Function
            # แต่ในตัวอย่างนี้จะใช้ label ตัวแรกเพื่อทดสอบ
            target = labels[:, 0] if labels.size(1) > 0 else torch.zeros(images.size(0), dtype=torch.long).to(device)

            optimizer.zero_grad()
            outputs = model(images)
            loss = criterion(outputs, target)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item()

            if i % 5 == 0: # อัปเดต Log ทุก 5 batches
                progress = int((i + 1) / total_steps * 100)
                status = {
                    "status": "training",
                    "message": f"Epoch {epoch}/{total_epochs}, Batch {i+1}/{total_steps}",
                    "current_epoch": epoch,
                    "total_epochs": total_epochs,
                    "epoch_progress": progress,
                    "loss": f"{loss.item():.4f}"
                }
                write_log(status, log_file)
        
        # คำนวณเวลาและ loss เฉลี่ย
        epoch_time = time.time() - epoch_start_time
        avg_epoch_loss = epoch_loss / total_steps
        print(f"Epoch {epoch}/{total_epochs}, Average Loss: {avg_epoch_loss:.4f}, Time: {epoch_time:.2f}s")

        # --- ส่วนที่ 5: การบันทึก Checkpoint ---
        if epoch % 10 == 0 or epoch == total_epochs:
            checkpoint_name = f"model_epoch_{epoch}.pth"
            model_path = os.path.join(os.path.dirname(__file__), '..', 'models', checkpoint_name)
            os.makedirs(os.path.dirname(model_path), exist_ok=True)
            
            # บันทึกโมเดล
            torch.save({
                'epoch': epoch,
                'model_state_dict': model.state_dict(),
                'optimizer_state_dict': optimizer.state_dict(),
                'loss': avg_epoch_loss,
                'vocab_size': real_dataset.vocab_size,
                'char_to_idx': real_dataset.char_to_idx,
                'idx_to_char': real_dataset.idx_to_char
            }, model_path)
            
            print(f"Checkpoint saved: {checkpoint_name}")

    final_status = {
        "status": "completed", 
        "message": "Training completed successfully!", 
        "epoch_progress": 100,
        "final_loss": f"{avg_epoch_loss:.4f}",
        "total_epochs": total_epochs,
        "model_saved": f"model_epoch_{total_epochs}.pth"
    }
    write_log(final_status, log_file)
    print("Training process finished.")


if __name__ == '__main__':
    try:
        epochs_to_run = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        train_on_gpu(epochs_to_run)
    except Exception as e:
        error_msg = f"Training error: {str(e)}"
        print(error_msg)
        write_log({"status": "error", "message": error_msg}, "training_log.txt")
        sys.exit(1)