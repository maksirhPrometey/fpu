/* Quill rich-text widget for Django admin.
 * Depends on quill.min.js (loaded before this file via Widget.Media).
 *
 * Features:
 *  - Rich-text editing with toolbar
 *  - Image upload to Cloudinary via admin endpoint
 *  - Image resize toolbar (click image → size picker)
 */
(function () {
    'use strict';

    /* ── Helpers ────────────────────────────────────────────────────────── */

    function getCsrfToken() {
        var match = document.cookie
            .split(';')
            .map(function (c) { return c.trim(); })
            .find(function (c) { return c.startsWith('csrftoken='); });
        return match ? match.slice('csrftoken='.length) : '';
    }

    function setOverlay(wrapper, visible) {
        var overlay = wrapper.querySelector('.quill-upload-overlay');
        if (overlay) {
            overlay.classList.toggle('quill-upload-overlay--active', visible);
        }
    }

    function buildOverlay() {
        var el = document.createElement('div');
        el.className = 'quill-upload-overlay';
        el.innerHTML =
            '<div class="quill-upload-spinner"></div>' +
            '<span>Завантаження зображення\u2026</span>';
        return el;
    }

    /* ── Image resize toolbar ───────────────────────────────────────────── */

    var _imgToolbar = null;      // singleton floating panel
    var _activeImg  = null;      // currently selected <img>

    var SIZE_PRESETS = [
        { label: '25%',  value: '25%'  },
        { label: '50%',  value: '50%'  },
        { label: '75%',  value: '75%'  },
        { label: '100%', value: '100%' },
    ];

    var ALIGN_PRESETS = [
        { label: '\u2190 Ліво',   align: 'left'   },
        { label: '\u2194 Центр',  align: 'center' },
        { label: '\u2192 Право',  align: 'right'  },
    ];

    function getImgToolbar() {
        if (_imgToolbar) return _imgToolbar;

        var bar = document.createElement('div');
        bar.className = 'quill-img-toolbar';
        bar.setAttribute('role', 'toolbar');
        bar.setAttribute('aria-label', 'Розмір зображення');

        var sizeGroup = document.createElement('div');
        sizeGroup.className = 'quill-img-toolbar__group';

        SIZE_PRESETS.forEach(function (preset) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'quill-img-btn';
            btn.dataset.size = preset.value;
            btn.textContent = preset.label;
            btn.title = 'Ширина ' + preset.label;
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (!_activeImg) return;
                _activeImg.style.width = preset.value;
                _activeImg.style.height = 'auto';
                if (preset.value === '100%') {
                    _activeImg.style.display = 'block';
                }
                updateActiveBtn(bar, 'data-size', preset.value);
                notifyQuillChange(_activeImg);
            });
            sizeGroup.appendChild(btn);
        });

        var sep = document.createElement('span');
        sep.className = 'quill-img-toolbar__sep';

        var alignGroup = document.createElement('div');
        alignGroup.className = 'quill-img-toolbar__group';

        ALIGN_PRESETS.forEach(function (preset) {
            var btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'quill-img-btn';
            btn.dataset.align = preset.align;
            btn.textContent = preset.label;
            btn.title = 'Вирівняти: ' + preset.label;
            btn.addEventListener('click', function (e) {
                e.preventDefault();
                e.stopPropagation();
                if (!_activeImg) return;
                applyAlign(_activeImg, preset.align);
                updateActiveBtn(bar, 'data-align', preset.align);
                notifyQuillChange(_activeImg);
            });
            alignGroup.appendChild(btn);
        });

        var closeBtn = document.createElement('button');
        closeBtn.type = 'button';
        closeBtn.className = 'quill-img-btn quill-img-btn--close';
        closeBtn.textContent = '\u00d7';
        closeBtn.title = 'Закрити';
        closeBtn.addEventListener('click', function (e) {
            e.preventDefault();
            e.stopPropagation();
            hideImgToolbar();
        });

        bar.appendChild(sizeGroup);
        bar.appendChild(sep);
        bar.appendChild(alignGroup);
        bar.appendChild(closeBtn);

        document.body.appendChild(bar);
        _imgToolbar = bar;
        return bar;
    }

    function applyAlign(img, align) {
        img.style.marginLeft  = '';
        img.style.marginRight = '';
        img.style.float       = '';
        img.style.display     = 'block';

        if (align === 'center') {
            img.style.marginLeft  = 'auto';
            img.style.marginRight = 'auto';
        } else if (align === 'right') {
            img.style.marginLeft  = 'auto';
            img.style.marginRight = '0';
        }
        // left: defaults (no extra margin)
    }

    function updateActiveBtn(bar, attr, value) {
        bar.querySelectorAll('[' + attr + ']').forEach(function (btn) {
            btn.classList.toggle(
                'quill-img-btn--active',
                btn.dataset[attr.replace('data-', '')] === value
            );
        });
    }

    function notifyQuillChange(img) {
        /* Trigger a synthetic input on the closest textarea so syncToTextarea fires */
        var wrapper = img.closest('.quill-wrapper');
        if (!wrapper) return;
        var textarea = wrapper.querySelector('.quill-textarea');
        if (!textarea) return;
        var editor = wrapper.querySelector('.ql-editor');
        if (!editor) return;
        textarea.value = editor.innerHTML === '<p><br></p>' ? '' : editor.innerHTML;
    }

    function showImgToolbar(img) {
        _activeImg = img;
        var bar = getImgToolbar();

        /* Reflect current width in buttons */
        var curW = img.style.width || '';
        updateActiveBtn(bar, 'data-size', curW);

        /* Reflect current alignment */
        var curAlign = 'left';
        if (img.style.marginLeft === 'auto' && img.style.marginRight === 'auto') {
            curAlign = 'center';
        } else if (img.style.marginLeft === 'auto') {
            curAlign = 'right';
        }
        updateActiveBtn(bar, 'data-align', curAlign);

        bar.style.display = 'flex';
        positionToolbar(img, bar);
    }

    function hideImgToolbar() {
        if (_imgToolbar) _imgToolbar.style.display = 'none';
        if (_activeImg) {
            _activeImg.classList.remove('quill-img--selected');
            _activeImg = null;
        }
    }

    function positionToolbar(img, bar) {
        var rect = img.getBoundingClientRect();
        var scrollY = window.pageYOffset || document.documentElement.scrollTop;
        var scrollX = window.pageXOffset || document.documentElement.scrollLeft;

        /* Prefer above the image; fall back to below if not enough room */
        var topAbove = rect.top + scrollY - bar.offsetHeight - 8;
        var top = topAbove > scrollY ? topAbove : rect.bottom + scrollY + 8;

        var left = rect.left + scrollX;
        var maxLeft = window.innerWidth - bar.offsetWidth - 12;
        left = Math.max(8, Math.min(left, maxLeft));

        bar.style.top  = top  + 'px';
        bar.style.left = left + 'px';
    }

    /* ── Image click handler ─────────────────────────────────────────────  */

    function attachImageClickHandler(quill) {
        quill.root.addEventListener('click', function (e) {
            var target = e.target;
            if (target && target.tagName === 'IMG') {
                e.stopPropagation();
                if (_activeImg && _activeImg !== target) {
                    _activeImg.classList.remove('quill-img--selected');
                }
                target.classList.add('quill-img--selected');
                showImgToolbar(target);
            } else {
                hideImgToolbar();
            }
        });

        /* Hide on scroll so the floating bar doesn't drift */
        document.addEventListener('scroll', function () {
            if (_activeImg) positionToolbar(_activeImg, getImgToolbar());
        }, { passive: true });

        /* Hide when clicking outside */
        document.addEventListener('click', function (e) {
            if (
                _activeImg &&
                !e.target.closest('.quill-img-toolbar') &&
                e.target !== _activeImg
            ) {
                hideImgToolbar();
            }
        });
    }

    /* ── Main init ───────────────────────────────────────────────────────  */

    function initQuill(wrapper) {
        if (wrapper._quillInit) return;
        wrapper._quillInit = true;

        var uploadUrl = wrapper.dataset.uploadUrl;
        var editorEl  = wrapper.querySelector('.quill-editor');
        var textarea  = wrapper.querySelector('.quill-textarea');

        if (!editorEl || !textarea) return;

        wrapper.appendChild(buildOverlay());

        var quill = new Quill(editorEl, {
            theme: 'snow',
            placeholder: 'Введіть текст статті\u2026',
            modules: {
                toolbar: {
                    container: [
                        [{ header: [2, 3, 4, false] }],
                        ['bold', 'italic', 'underline', 'strike'],
                        [{ list: 'ordered' }, { list: 'bullet' }],
                        ['blockquote', 'link', 'image'],
                        [{ align: [] }],
                        ['clean'],
                    ],
                    handlers: {
                        image: function () {
                            var input = document.createElement('input');
                            input.type = 'file';
                            input.accept = 'image/jpeg,image/png,image/webp,image/gif';
                            input.click();

                            input.addEventListener('change', function () {
                                var file = input.files[0];
                                if (!file) return;

                                setOverlay(wrapper, true);

                                var formData = new FormData();
                                formData.append('image', file);

                                fetch(uploadUrl, {
                                    method: 'POST',
                                    body: formData,
                                    headers: { 'X-CSRFToken': getCsrfToken() },
                                })
                                    .then(function (resp) {
                                        if (!resp.ok) {
                                            return resp.json().then(function (data) {
                                                throw new Error(data.error || 'HTTP ' + resp.status);
                                            });
                                        }
                                        return resp.json();
                                    })
                                    .then(function (data) {
                                        if (data.url) {
                                            var range = quill.getSelection(true);
                                            quill.insertEmbed(
                                                range.index,
                                                'image',
                                                data.url,
                                                Quill.sources.USER
                                            );
                                            quill.setSelection(
                                                range.index + 1,
                                                Quill.sources.SILENT
                                            );
                                        }
                                    })
                                    .catch(function (err) {
                                        alert('Помилка завантаження: ' + err.message);
                                    })
                                    .finally(function () {
                                        setOverlay(wrapper, false);
                                    });
                            });
                        },
                    },
                },
            },
        });

        if (textarea.value.trim()) {
            quill.root.innerHTML = textarea.value;
        }

        function syncToTextarea() {
            var html = quill.root.innerHTML;
            textarea.value = html === '<p><br></p>' ? '' : html;
        }

        quill.on('text-change', syncToTextarea);

        var form = wrapper.closest('form');
        if (form) {
            form.addEventListener('submit', syncToTextarea);
        }

        attachImageClickHandler(quill);
    }

    function initAll() {
        document.querySelectorAll('.quill-wrapper').forEach(initQuill);
    }

    function ready(fn) {
        if (typeof Quill === 'undefined') {
            var attempts = 0;
            var poll = setInterval(function () {
                attempts++;
                if (typeof Quill !== 'undefined') {
                    clearInterval(poll);
                    fn();
                } else if (attempts > 50) {
                    clearInterval(poll);
                    console.error('Quill.js failed to load within 5 s');
                }
            }, 100);
        } else if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', fn);
        } else {
            fn();
        }
    }

    ready(initAll);
})();
