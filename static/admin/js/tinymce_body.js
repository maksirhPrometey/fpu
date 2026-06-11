'use strict';

/**
 * TinyMCE helpers for FPU admin (light editor + image upload with CSRF).
 */

function fpsuGetCsrfToken() {
    var match = document.cookie
        .split(';')
        .map(function (c) { return c.trim(); })
        .find(function (c) { return c.startsWith('csrftoken='); });
    return match ? match.slice('csrftoken='.length) : '';
}

function fpsuTinyMceUploadHandler(blobInfo, progress) {
    return new Promise(function (resolve, reject) {
        var formData = new FormData();
        formData.append('image', blobInfo.blob(), blobInfo.filename());

        var xhr = new XMLHttpRequest();
        xhr.open('POST', '/admin/news/article/upload-image/');
        xhr.setRequestHeader('X-CSRFToken', fpsuGetCsrfToken());

        xhr.upload.onprogress = function (event) {
            if (event.lengthComputable) {
                progress(event.loaded / event.total * 100);
            }
        };

        xhr.onload = function () {
            if (xhr.status < 200 || xhr.status >= 300) {
                try {
                    reject(JSON.parse(xhr.responseText).error || 'Помилка завантаження');
                } catch (err) {
                    reject('Помилка завантаження');
                }
                return;
            }
            try {
                var data = JSON.parse(xhr.responseText);
                if (data.url) {
                    resolve(data.url);
                } else {
                    reject('Сервер не повернув URL зображення');
                }
            } catch (err) {
                reject('Некоректна відповідь сервера');
            }
        };

        xhr.onerror = function () {
            reject('Помилка мережі');
        };

        xhr.send(formData);
    });
}

function fpsuTinyMceSetup(editor) {
    editor.on('PostRender', function () {
        var container = editor.getContainer();
        if (container) {
            container.classList.add('fpsu-tinymce', 'fpsu-tinymce--light');
        }
    });
}
