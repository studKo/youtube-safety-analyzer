// new/static/transcribe.js

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('youtube-url-form');
    const urlInput = document.getElementById('youtube-url');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('analysis-result');
    const loadingStatus = document.getElementById('loading-status');
    
    const fileExplorerBtn = document.getElementById('file-explorer-btn');
    const fileInput = document.getElementById('video-file-input');
    let selectedFile = null;

    const modelButtons = document.querySelectorAll('.model-btn');
    let selectedModel = 'beomi/kcbert-large';

    modelButtons.forEach(button => {
        button.addEventListener('click', function() {
            modelButtons.forEach(btn => btn.classList.remove('active'));
            this.classList.add('active');
            selectedModel = this.id;
        });
    });

    fileExplorerBtn.addEventListener('click', function() {
        fileInput.click();
    });

    fileInput.addEventListener('change', function() {
        if (this.files && this.files.length > 0) {
            selectedFile = this.files[0];
            urlInput.value = selectedFile.name;
            urlInput.readOnly = true;
        }
    });

    urlInput.addEventListener('click', function() {
        selectedFile = null;
        fileInput.value = '';
        urlInput.readOnly = false;
    });

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        
        loadingDiv.style.display = 'block';
        resultDiv.innerHTML = '';
        
        const messages = [
            "영상/파일 다운로드 중...",
            "음성 추출 및 변환 중... (시간이 가장 오래 소요됩니다)",
            "텍스트 감성 분석 중...",
            "결과를 정리하는 중..."
        ];
        let messageIndex = 0;
        
        // 첫 메시지를 즉시 설정하여 변화를 확실히 보여줍니다.
        loadingStatus.textContent = messages[messageIndex];
        
        // 타이머를 설정하지만, 시스템 부하로 인해 정상 작동하지 않을 수 있습니다.
        const intervalId = setInterval(() => {
            messageIndex = (messageIndex + 1) % messages.length;
            loadingStatus.textContent = messages[messageIndex];
        }, 7000); // 간격을 7초로 늘려 변화 가능성을 높임

        const csrftoken = getCookie('csrftoken');
        let requestBody;
        let headers = { 'X-CSRFToken': csrftoken };

        if (selectedFile) {
            requestBody = new FormData();
            requestBody.append('video_file', selectedFile);
            requestBody.append('sentiment_model', selectedModel);
        } else {
            requestBody = JSON.stringify({
                'url': urlInput.value,
                'sentiment_model': selectedModel
            });
            headers['Content-Type'] = 'application/json';
        }

        fetch('/youtube/api/analyze/', {
            method: 'POST',
            headers: headers,
            body: requestBody
        })
        .then(response => {
            if (response.redirected) {
                window.location.href = response.url;
                return;
            }
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || '서버 응답에 문제가 있습니다.') });
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            if (data.status === 'success' && data.redirect_url) {
                window.location.href = data.redirect_url;
            } else {
                throw new Error(data.message || '알 수 없는 오류가 발생했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = `<p style="color: red;">분석 중 오류가 발생했습니다: ${error.message}</p>`;
        })
        .finally(() => {
            clearInterval(intervalId); // 분석이 끝나면 타이머를 확실히 중지
            loadingDiv.style.display = 'none';
        });
    });
});

function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}