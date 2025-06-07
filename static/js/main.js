document.addEventListener('DOMContentLoaded', () => {
    let eventSource = null;

    const fontUploadBtn = document.getElementById('font-upload-btn');
    const corpusUploadBtn = document.getElementById('corpus-upload-btn');
    const fontFileInput = document.getElementById('font-file-input');
    const corpusFileInput = document.getElementById('corpus-file-input');
    const fontList = document.getElementById('font-list');
    const generateBtn = document.getElementById('generate-dataset-btn');
    const startTrainingBtn = document.getElementById('start-training-btn');

    const datasetStatusArea = document.getElementById('dataset-status-area');
    const datasetLog = document.getElementById('dataset-log');
    const datasetProgressBar = document.getElementById('dataset-progress-bar');

    const trainingLog = document.getElementById('training-log');
    const trainingProgressBar = document.getElementById('training-progress-bar');
    const epochsInput = document.getElementById('epochs-input');

    async function uploadFile(url, file) {
        const formData = new FormData();
        formData.append('file', file);
        const response = await fetch(url, {
            method: 'POST',
            body: formData
        });
        return response.json();
    }

    async function updateFontList() {
        const response = await fetch('/list/fonts');
        const result = await response.json();
        fontList.innerHTML = '';
        if (result.files.length === 0) {
            fontList.innerHTML = '<li>ยังไม่มีฟอนต์ที่อัปโหลด</li>';
        } else {
            result.files.forEach(file => {
                const li = document.createElement('li');
                li.textContent = file;
                fontList.appendChild(li);
            });
        }
    }

    fontUploadBtn.addEventListener('click', async () => {
        fontList.innerHTML = '<li>⏳ กำลังอัปโหลดฟอนต์...</li>';
        for (const file of fontFileInput.files) {
            await uploadFile('/upload/font', file);
        }
        await updateFontList();
    });

    corpusUploadBtn.addEventListener('click', async () => {
        if (corpusFileInput.files.length > 0) {
            await uploadFile('/upload/corpus', corpusFileInput.files[0]);
            alert('✅ อัปโหลด Corpus สำเร็จ');
        }
    });

    generateBtn.addEventListener('click', async () => {
        const fontResponse = await fetch('/list/fonts');
        const fontData = await fontResponse.json();
        if (!fontData.files || fontData.files.length === 0) {
            alert('⚠️ กรุณาอัปโหลดฟอนต์ก่อนสร้าง Dataset');
            return;
        }

        generateBtn.disabled = true;
        datasetStatusArea.style.display = 'block';
        datasetProgressBar.style.width = '0%';
        datasetProgressBar.textContent = 'เริ่มต้น...';
        datasetLog.textContent = '';

        await fetch('/generate-dataset', { method: 'POST' });

        if (eventSource) eventSource.close();
        eventSource = new EventSource('/dataset-status');

        eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            datasetLog.textContent = JSON.stringify(data, null, 2);

            if (data.status === 'generating') {
                const progress = data.progress || 0;
                datasetProgressBar.style.width = `${progress}%`;
                datasetProgressBar.textContent = `${progress}%`;
            } else if (data.status === 'completed' || data.status === 'error') {
                const progress = data.progress || (data.status === 'completed' ? 100 : 0);
                datasetProgressBar.style.width = `${progress}%`;
                datasetProgressBar.textContent = data.status === 'completed' ? 'เสร็จสิ้น!' : 'เกิดข้อผิดพลาด!';
                eventSource.close();
                generateBtn.disabled = false;
            }
        };
    });

    startTrainingBtn.addEventListener('click', () => {
        if (eventSource) eventSource.close();

        startTrainingBtn.disabled = true;
        startTrainingBtn.textContent = '...กำลังฝึกสอน...';

        const epochs = parseInt(epochsInput.value);
        fetch('/start-training', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ epochs })
        }).then(() => {
            eventSource = new EventSource('/training-status');

            eventSource.onmessage = (event) => {
                const data = JSON.parse(event.data);
                trainingLog.textContent = JSON.stringify(data, null, 2);
                trainingLog.scrollTop = trainingLog.scrollHeight;

                if (data.status === 'training') {
                    const progress = data.epoch_progress || 0;
                    trainingProgressBar.style.width = `${progress}%`;
                    trainingProgressBar.textContent = `Epoch ${data.current_epoch}: ${progress}%`;
                } else if (data.status === 'completed') {
                    trainingProgressBar.style.width = '100%';
                    trainingProgressBar.textContent = 'เสร็จสิ้น!';
                    eventSource.close();
                    startTrainingBtn.disabled = false;
                    startTrainingBtn.textContent = '⚡️ เริ่มการฝึกสอนด้วย GPU';
                } else if (data.status === 'initializing') {
                    trainingProgressBar.style.width = '0%';
                    trainingProgressBar.textContent = 'กำลังเตรียมการ...';
                }
            };

            eventSource.onerror = () => {
                trainingLog.textContent += '\n🚨 เกิดข้อผิดพลาดในการเชื่อมต่อกับเซิร์ฟเวอร์';
                eventSource.close();
                startTrainingBtn.disabled = false;
                startTrainingBtn.textContent = '⚡️ เริ่มการฝึกสอนด้วย GPU';
            };
        });
    });

    updateFontList();
});
