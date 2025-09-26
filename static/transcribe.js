// new/static/transcribe.js

document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('youtube-url-form');
    const urlInput = document.getElementById('youtube-url');
    const loadingDiv = document.getElementById('loading');
    const resultDiv = document.getElementById('analysis-result');

    form.addEventListener('submit', function(event) {
        event.preventDefault();
        const youtubeUrl = urlInput.value;
        
        loadingDiv.style.display = 'block';
        resultDiv.innerHTML = '';
        const csrftoken = getCookie('csrftoken');

        fetch('/youtube/api/analyze/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            body: JSON.stringify({ 'url': youtubeUrl })
        })
        .then(response => {
            if (!response.ok) {
                return response.json().then(err => { throw new Error(err.message || '서버 응답에 문제가 있습니다.') });
            }
            return response.json();
        })
        .then(data => {
            if (data.status === 'success' && data.redirect_url) {
                window.location.href = data.redirect_url;
            } else if (data.status === 'age_restricted') {
                alert(data.message);
            } else {
                throw new Error(data.message || '알 수 없는 오류가 발생했습니다.');
            }
        })
        .catch(error => {
            console.error('Error:', error);
            resultDiv.innerHTML = `<p style="color: red;">분석 중 오류가 발생했습니다: ${error.message}</p>`;
        })
        .finally(() => {
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