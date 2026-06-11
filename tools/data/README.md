# tools/data/ — Файли даних для імпорту з Joomla

Ця папка **git-ignored** — великі файли сюди не потрапляють у репозиторій.

Перед запуском `import_all` потрібно покласти відповідні файли сюди.

---

## Список файлів

| Файл | Розмір | Звідки береться | Потрібен для |
|---|---|---|---|
| `fpsu_seo_dump.sql` | ~280 MB | MySQL dump з Joomla сервера | крок 0 (генерація JSON) |
| `cats.tsv` | ~50 KB | MySQL export (see SQL below) | `import_joomla` |
| `articles.tsv` | ~5 MB | MySQL export (see SQL below) | `import_joomla`, `link_article_covers` |
| `content_bodies.json` | ~244 MB | генерується `parse_bodies.py` | `import_bodies`, `import_missing_articles` |
| `menu.tsv` | ~200 KB | MySQL export (see SQL below) | `import_pages`, `import_bodies --pages` |
| `seo_inventory.json` | ~26 MB | генерується `parse_joomla_dump.py` | аналіз SEO |

---

## SQL-запити для генерації TSV файлів

### cats.tsv
```sql
SELECT id, alias, title, path, metadesc, metakey
INTO OUTFILE '/tmp/cats.tsv'
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
FROM zeki2_categories
WHERE published = 1;
```

### articles.tsv
```sql
SELECT id, alias, catid, title, metadesc, metakey, images, publish_up
INTO OUTFILE '/tmp/articles.tsv'
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
FROM zeki2_content;
```

### menu.tsv
```sql
SELECT id, title, alias, path, link, type, parent_id
INTO OUTFILE '/tmp/menu.tsv'
FIELDS TERMINATED BY '\t'
LINES TERMINATED BY '\n'
FROM zeki2_menu
WHERE published = 1;
```

---

## Порядок підготовки файлів

### 1. Зроби MySQL dump (на Joomla сервері)
```bash
mysqldump -u USER -p DATABASE zeki2_content > fpsu_seo_dump.sql
```

### 2. Скопіюй dump локально через SCP
```bash
scp -P 9092 -i key_dig_priv.pem root@78.27.236.224:/path/to/fpsu_seo_dump.sql tools/data/
```

### 3. Генеруй content_bodies.json
```bash
python tools/parse_bodies.py
# читає: tools/data/fpsu_seo_dump.sql
# пише:  tools/data/content_bodies.json
```

### 4. Отримай TSV файли
Виконай SQL-запити вище в phpMyAdmin або через mysql client, збережи у `tools/data/`.

### 5. Запускай import
```bash
python manage.py import_all
# або крок за кроком:
python manage.py import_joomla
python manage.py import_bodies --rewrite-images
python manage.py import_missing_articles --rewrite-images
python manage.py import_pages
python manage.py import_bodies --pages --rewrite-images
python manage.py seed_section_pages
python manage.py link_article_covers   # потребує articles.tsv + media/joomla_images/
```

---

## Зображення на VPS

Медіа зберігаються локально в `media/` (Docker volume). Після rsync з Joomla:

```bash
# На сервері (Docker):
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec web \
  python manage.py link_article_covers

# Або повний імпорт з архіву даних:
DATA_ARCHIVE_URL=https://.../fpu_data.tar.gz ./seed_all.sh
```

Для синхронізації з Joomla-сервера (локально):

```bash
./tools/fetch_from_remote.sh
```
