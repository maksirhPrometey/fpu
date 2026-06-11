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
├── verify_urls.py           ← перевіряє доступність URL
├── fetch_from_remote.sh     ← стягнути dump + TSV з Joomla-сервера
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

# 4. Обкладинки статей (локальні WebP з media/joomla_images/):
python manage.py link_article_covers

# 5. Документи:
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
| 8 | `link_article_covers` | Обкладинки статей → Article.local_image |
| 9 | `seed_documents` | Документи ФПУ |

---

## Синхронізація з живими джерелами

```bash
python manage.py sync_spo_home       # блоки spo.fpsu.org.ua на головній
python manage.py sync_spo_blog       # блог SPO
python manage.py sync_menu_news_live # новини з меню
python manage.py audit_media         # перевірка доступності медіа
```

---

## Зображення на сервері

Медіафайли зберігаються локально в `media/` (Docker volume `media_volume`).
Після rsync з Joomla-сервера:

```bash
# Локально або на VPS:
python manage.py link_article_covers
python manage.py import_gallery
```

Для синхронізації з Joomla-сервера:

```bash
./tools/fetch_from_remote.sh
```
