# tools/ — Утиліти та дані для міграції з Joomla

## Структура

```
tools/
├── data/                    ← великі файли даних (git-ignored, div README.md)
│   ├── README.md            ← інструкція звідки брати файли
│   ├── cats.tsv             ← [потрібно покласти] категорії з MySQL
│   ├── articles.tsv         ← [потрібно покласти] статті з MySQL
│   ├── content_bodies.json  ← [генерується] тіла статей
│   ├── menu.tsv             ← [потрібно покласти] меню з MySQL
│   └── fpsu_seo_dump.sql    ← [потрібно покласти] MySQL dump
│
├── gallery_cats.json        ← [в git] категорії JoomGallery
├── gallery.json             ← [в git] фото JoomGallery
├── tags.json                ← [в git] теги
│
├── parse_bodies.py          ← парсить SQL dump → content_bodies.json
├── parse_joomla_dump.py     ← будує seo_inventory.json з TSV файлів
├── extract_tsv.py           ← витягує TSV таблиці з SQL dump
├── merge_articles.py        ← об'єднує дублікати статей
├── clean_html.py            ← очищає HTML тіла статей
├── convert_to_webp.py       ← конвертує зображення в WebP
├── replace_image_paths.py   ← замінює шляхи зображень у HTML
├── upload_images_cloudinary.py ← завантажує зображення в Cloudinary
├── verify_urls.py           ← перевіряє доступність URL
└── _server_dump.py          ← утиліта dump з Joomla сервера
```

---

## Швидкий старт — повний імпорт

```bash
# 1. Підготуй файли (div tools/data/README.md)

# 2. Dry-run (нічого не пише в БД):
python manage.py import_all --dry-run

# 3. Реальний імпорт:
python manage.py import_all

# 4. Зображення в Cloudinary (потрібен SSH ключ):
python manage.py import_images --ssh-key key_dig_priv.pem

# 5. Зображення з тіл статей:
python manage.py import_body_images --workers 8

# 6. Документи:
python manage.py seed_documents
```

---

## Покрокові команди

| Крок | Команда | Опис |
|------|---------|------|
| 1 | `import_joomla` | Категорії + метадані статей (без тіл) |
| 2 | `import_bodies` | Наповнення Article.body |
| 3 | `import_missing_articles` | Статті що є в дампі але не в БД |
| 4 | `import_pages` | StaticPage записи з меню |
| 5 | `import_bodies --pages` | Тіла для статичних сторінок |
| 6 | `seed_section_pages` | Навігаційні розділи (хардкожено) |
| 7 | `import_gallery` | Альбоми + фото |
| 8 | `import_images` | Обкладинки статей → Cloudinary |
| 9 | `import_body_images` | Зображення з тіл → Cloudinary |
| 10 | `seed_documents` | Документи ФПУ |
