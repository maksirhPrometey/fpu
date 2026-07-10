# 🚀 Інструкція для Деплойменту - Змінення Кольорової Схеми на Блакитний

## Коміт
```
421209f feat: change primary color scheme from navy blue to teal
```

## Сервер
- **URL**: testwww.fpsu.org.ua (62.80.171.14)
- **Шлях**: /mnt_data/fpsu
- **Тип**: Docker (docker-compose + PostgreSQL)

## Кроки для деплойменту

### 1. На сервері: Оновити код
```bash
cd /mnt_data/fpsu
git pull origin main
```

### 2. Перебудувати та перезапустити контейнери
```bash
bash deploy/docker/deploy.sh
```
або якщо використовується HTTPS:
```bash
USE_HTTPS=true bash deploy/docker/deploy.sh
```

### 3. Перевірити результат
```bash
# Перевірити health check
curl http://testwww.fpsu.org.ua/healthz/

# Перевірити логи
docker compose logs -f web

# Перейти на сайт
https://testwww.fpsu.org.ua/
```

## Що змінилось

### Кольорова схема: Синій → Блакитний (Teal)

| Елемент | Старий | Новий | RGB |
|---------|--------|-------|-----|
| Primary | #133a7c | #0d8fa3 | rgb(13, 143, 163) |
| Primary-700 | #0f2c66 | #067a8b | rgb(6, 122, 139) |
| Primary-900 | #0a1f4a | #054d5f | rgb(5, 77, 95) |
| Panel | #0f2c66 | #067a8b | rgb(6, 122, 139) |
| Mobile theme-color | #0f2c66 | #0d8fa3 | rgb(13, 143, 163) |

### Змінені файли (13 CSS + 1 HTML)
- `static/css/tokens.css` — основні дизайн-токени
- `static/css/base.css` — кнопки, selection, shadows
- `static/css/header.css` — шапка сайту
- `static/css/hero.css` — hero банер
- `static/css/priorities.css` — панель пріоритетів
- `static/css/news_slider.css` — карусель новин
- `static/css/news_list.css` — список новин
- `static/css/forms.css` — форми
- `static/css/search.css` — пошук
- `static/css/prose.css` — текстовий вміст
- `static/css/documents.css` — документи
- `static/css/static_page.css` — статичні сторінки
- `static/css/home_extras.css` — додатки на головній
- `templates/base.html` — meta theme-color для мобільних браузерів

### RGBA Тіні
Всі RGBA тіні оновлені:
- `rgba(15, 44, 102, ...)` → `rgba(6, 122, 139, ...)`
- `rgba(19, 58, 124, ...)` → `rgba(13, 143, 163, ...)`
- `rgba(10, 31, 74, ...)` → `rgba(5, 77, 95, ...)`

## Откат (якщо потрібно)
```bash
cd /mnt_data/fpsu
git revert 421209f
bash deploy/docker/deploy.sh
```

## Статус Git
```bash
cd /mnt_data/fpsu
git log --oneline -5
git status
```

## Перевірка результатів
Після деплойменту колір має бути **блакитним (teal)** замість темно-синього:
- Шапка сайту
- Кнопки
- Лінки
- Панель пріоритетів
- Карусель новин
- Мобільна тема (address bar на iOS)
