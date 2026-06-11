"""Hub section pages — description, child links, optional news category.

Shared by seed_section_pages and StaticPage admin (sub-page edit links).
"""
from __future__ import annotations

import re
from urllib.parse import urlencode

from django.urls import reverse

from apps.pages.menu_news import news_category_for_menu_path

_BODY_LINK_RE = re.compile(
    r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>([^<]+)</a>',
    re.IGNORECASE,
)
_ARTICLE_HREF_RE = re.compile(
    r"^/(?P<cat>[\w-]+(?:/[\w-]+)*)/(?P<jid>\d+)-(?P<slug>[\w-]+)\.html$",
)

# url_path → title, description, children, news_category_path
SECTION_PAGE_DEFS: list[dict] = [
    {
        "url_path": "/pro-fpu",
        "title": "Про ФПУ",
        "description": (
            "Федерація профспілок України — найбільше об'єднання профспілок країни, "
            "що об'єднує мільйони працівників різних галузей. Ми захищаємо трудові права, "
            "забезпечуємо гідні умови праці та відстоюємо соціальну справедливість."
        ),
        "children": [
            ("Історія ФПУ", "/pro-fpu/istoriya-fpu"),
            ("Виборні органи ФПУ", "/pro-fpu/viborchi-organi-fpu"),
            ("Керівництво ФПУ", "/pro-fpu/kerivnitstvo-fpu"),
            ("Президія", "/pro-fpu/prezidiya"),
            ("Членські організації", "/pro-fpu/chlenski-organizatsiji"),
            ("Комісії ФПУ", "/pro-fpu/komissii-fpu"),
            ("Законодавче регулювання діяльності", "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok"),
            ("Символіка ФПУ", "/pro-fpu/simvolika-fpu"),
        ],
        "news_category_path": None,
    },
    {
        "url_path": "/pro-fpu/kerivnitstvo-fpu",
        "title": "Керівництво ФПУ",
        "description": (
            "Федерацію профспілок України очолює обраний з'їздом Голова ФПУ. "
            "Керівництво здійснює загальне управління діяльністю Федерації, "
            "представляє її інтереси у відносинах з органами державної влади, "
            "роботодавцями та міжнародними організаціями."
        ),
        "children": [
            ("Виборні органи ФПУ", "/pro-fpu/viborchi-organi-fpu"),
            ("Президія ФПУ", "/pro-fpu/prezidiya"),
            ("Комісії ФПУ", "/pro-fpu/komissii-fpu"),
        ],
        "news_category_path": None,
    },
    {
        "url_path": "/pro-fpu/chlenski-organizatsiji",
        "title": "Членські організації ФПУ",
        "description": (
            "До складу Федерації профспілок України входять всеукраїнські галузеві профспілки "
            "та територіальні об'єднання організацій профспілок. Вони об'єднують мільйони "
            "членів у всіх регіонах та галузях економіки України."
        ),
        "children": [
            (
                "Всеукраїнські галузеві профспілки",
                "/pro-fpu/chlenski-organizatsiji/vseukrajinski-galuzevi-profspilki",
            ),
            (
                "Територіальні об'єднання організацій профспілок",
                "/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok",
            ),
        ],
        "news_category_path": "nasha-borotba/novini-chlenskikh-organizatsij",
    },
    {
        "url_path": "/pro-fpu/komissii-fpu",
        "title": "Комісії ФПУ",
        "description": (
            "Постійні комісії ФПУ є дорадчими органами Ради та Президії Федерації. "
            "Вони здійснюють підготовку і попередній розгляд питань, що стосуються "
            "основних напрямів діяльності профспілок."
        ),
        "children": [
            ("Виборні органи ФПУ", "/pro-fpu/viborchi-organi-fpu"),
            ("Президія ФПУ", "/pro-fpu/prezidiya"),
        ],
        "news_category_path": None,
    },
    {
        "url_path": "/pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok",
        "title": "Законодавче регулювання діяльності профспілок",
        "description": (
            "Діяльність профспілок в Україні регулюється Конституцією України, "
            "Законом України «Про професійні спілки, їх права та гарантії діяльності», "
            "Кодексом законів про працю та іншими нормативно-правовими актами."
        ),
        "children": [
            ("Документи ФПУ", "/documents"),
            ("Статут ФПУ", "/documents/statut-fpu"),
            ("Постанови Ради ФПУ", "/documents/postanovi-radi-fpu"),
            ("Постанови Президії ФПУ", "/documents/postanovi-prezidiji-fpu"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist",
    },
    {
        "url_path": "/napryamki-diyalnosti",
        "title": "Напрями діяльності",
        "description": (
            "ФПУ веде системну роботу за всіма ключовими напрямами захисту прав працівників: "
            "від правового супроводу до охорони праці, від соціального страхування до молодіжної "
            "і міжнародної діяльності."
        ),
        "children": [
            ("Правовий захист", "/napryamki-diyalnosti/pravovij-zakhist"),
            ("Охорона праці і здоров'я", "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya"),
            ("Соціальний захист", "/napryamki-diyalnosti/sotsialnij-zakhist"),
            ("Виробнича політика та ціноутворення", "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya"),
            ("Соціальне страхування і пенсійне забезпечення", "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"),
            ("Соціальний діалог та колективно-договірне регулювання", "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"),
            ("Організаційна робота", "/napryamki-diyalnosti/organizatsijna-robota"),
            ("Молодіжна політика", "/napryamki-diyalnosti/molodizhna-politika"),
            ("Інформаційна робота", "/napryamki-diyalnosti/informatsijna-robota"),
            ("Міжнародна робота", "/napryamki-diyalnosti/mizhnarodna-robota"),
        ],
        "news_category_path": None,
    },
    {
        "url_path": "/napryamki-diyalnosti/pravovij-zakhist",
        "title": "Правовий захист",
        "description": (
            "ФПУ здійснює системну правозахисну роботу: веде переговори з роботодавцями "
            "та органами влади, надає безоплатні юридичні консультації членам профспілок, "
            "представляє їхні інтереси у судах та перед державними органами. "
            "Правовий захист — ключовий напрям діяльності профспілкового руху."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Документи ФПУ", "/documents"),
            ("Постанови Ради ФПУ", "/documents/postanovi-radi-fpu"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist",
    },
    {
        "url_path": "/napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya",
        "title": "Охорона праці і здоров'я",
        "description": (
            "Профспілки забезпечують дотримання вимог законодавства про охорону праці, "
            "здійснюють громадський контроль за умовами праці та безпекою на виробництві. "
            "ФПУ бере активну участь у розробці нормативних актів у сфері охорони праці, "
            "взаємодіє з Державною службою з питань праці та роботодавцями."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Правовий захист", "/napryamki-diyalnosti/pravovij-zakhist"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/okhorona-pratsi-i-zdorov-ya",
    },
    {
        "url_path": "/napryamki-diyalnosti/sotsialnij-zakhist",
        "title": "Соціальний захист",
        "description": (
            "ФПУ відстоює гідний рівень заробітної плати, пенсій та соціальних виплат. "
            "Профспілки беруть участь у тристоронніх переговорах у рамках Національної "
            "тристоронньої соціально-економічної ради, домагаються підвищення мінімальної "
            "заробітної плати та індексації доходів відповідно до зростання цін."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Соціальний діалог", "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"),
            ("Соціальне страхування і пенсійне забезпечення", "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/sotsialnij-zakhist",
    },
    {
        "url_path": "/napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya",
        "title": "Виробнича політика та ціноутворення",
        "description": (
            "Профспілки беруть участь у формуванні державної промислової та цінової політики. "
            "ФПУ відстоює інтереси працівників у питаннях тарифного регулювання, "
            "збереження виробничого потенціалу країни та забезпечення зайнятості населення."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Соціальний захист", "/napryamki-diyalnosti/sotsialnij-zakhist"),
            ("Соціальний діалог", "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/vyrobnycha-polityka-ta-tsinoutvorennia",
    },
    {
        "url_path": "/napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya",
        "title": "Соціальне страхування і пенсійне забезпечення",
        "description": (
            "ФПУ представляє інтереси застрахованих осіб у фондах соціального страхування "
            "та Пенсійному фонді України. Профспілки беруть участь в управлінні системою "
            "соціального захисту, добиваються підвищення пенсій та страхових виплат, "
            "захисту прав працівників на гідне пенсійне забезпечення."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Соціальний захист", "/napryamki-diyalnosti/sotsialnij-zakhist"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya",
    },
    {
        "url_path": "/napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya",
        "title": "Соціальний діалог та колективно-договірне регулювання",
        "description": (
            "Соціальний діалог — ключовий інструмент взаємодії профспілок, роботодавців "
            "і держави. ФПУ бере участь у переговорах на всіх рівнях: від підприємства "
            "до національного. Колективні договори та угоди забезпечують гарантії "
            "трудових прав мільйонів найманих працівників."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Соціальний захист", "/napryamki-diyalnosti/sotsialnij-zakhist"),
            ("Постанови Ради ФПУ", "/documents/postanovi-radi-fpu"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/sotsialnij-dialog",
    },
    {
        "url_path": "/napryamki-diyalnosti/organizatsijna-robota",
        "title": "Організаційна робота",
        "description": (
            "Організаційна робота спрямована на зміцнення профспілкових лав, "
            "підвищення ефективності діяльності первинних організацій та забезпечення "
            "представництва інтересів членів профспілок на всіх рівнях. "
            "ФПУ підтримує навчання профспілкових кадрів і активістів."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Членські організації", "/pro-fpu/chlenski-organizatsiji"),
            ("Молодіжна політика", "/napryamki-diyalnosti/molodizhna-politika"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/organizatsionnaya-rabota",
    },
    {
        "url_path": "/napryamki-diyalnosti/molodizhna-politika",
        "title": "Молодіжна політика",
        "description": (
            "ФПУ приділяє особливу увагу роботі з молоддю. Молодіжні комісії та ради "
            "діють у складі профспілкових організацій усіх рівнів. Профспілки сприяють "
            "працевлаштуванню молоді, захищають її трудові права та інтереси, "
            "підтримують розвиток молодіжного активу."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Організаційна робота", "/napryamki-diyalnosti/organizatsijna-robota"),
            ("Членські організації", "/pro-fpu/chlenski-organizatsiji"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/molodizhna-politika",
    },
    {
        "url_path": "/napryamki-diyalnosti/informatsijna-robota",
        "title": "Інформаційна робота",
        "description": (
            "Інформаційна діяльність ФПУ спрямована на висвітлення роботи профспілок, "
            "формування позитивного іміджу профспілкового руху та інформування суспільства "
            "про захист трудових прав. ФПУ підтримує власні медіа та активно присутня "
            "у соціальних мережах."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Фотогалерея", "/gallery/"),
            ("Новини ФПУ", "/materiali/"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/informatsijna-robota",
    },
    {
        "url_path": "/napryamki-diyalnosti/mizhnarodna-robota",
        "title": "Міжнародна робота",
        "description": (
            "ФПУ є членом Міжнародної організації праці (МОП), Міжнародної конфедерації "
            "профспілок (МКП), Панєвропейської регіональної ради МКП та Загальноєвропейської "
            "ради профспілок (ЄКП). Міжнародна діяльність спрямована на захист прав "
            "трудових мігрантів та інтеграцію до European Trade Union Confederation."
        ),
        "children": [
            ("Напрями діяльності", "/napryamki-diyalnosti"),
            ("Новини ФПУ", "/materiali/"),
        ],
        "news_category_path": "informatsiya-za-napryamkami-diyalnosti/mizhnarodna-robota",
    },
    {
        "url_path": "/dokumenti-fpu",
        "title": "Документи ФПУ",
        "description": (
            "Офіційні документи Федерації профспілок України: постанови, статут, стратегія "
            "розвитку, матеріали з'їздів та інші нормативні акти, що регулюють діяльність "
            "профспілкового руху."
        ),
        "children": [
            ("Матеріали VII З'їзду ФПУ", "/documents/materialy-vii-zyizdu-fpu"),
            ("Матеріали VIII З'їзду ФПУ", "/documents/materialy-viii-zyizdu-fpu"),
            ("Постанови Ради ФПУ", "/documents/postanovi-radi-fpu"),
            ("Постанови Президії ФПУ", "/documents/postanovi-prezidiji-fpu"),
            ("Статут ФПУ", "/documents/statut-fpu"),
            ("Стратегія діяльності ФПУ 2021–2026", "/documents/strategiya-diyalnosti-fpu"),
            ("Репрезентативність", "/documents/reprezentativnist"),
        ],
        "news_category_path": None,
    },
]


def _normalize_path(url_path: str) -> str:
    return url_path.strip("/").removesuffix(".html")


def hub_info_for(url_path: str) -> dict | None:
    """Return hub section definition for a StaticPage url_path, if any."""
    clean = _normalize_path(url_path)
    for section in SECTION_PAGE_DEFS:
        if _normalize_path(section["url_path"]) == clean:
            if section.get("children") or section.get("news_category_path"):
                return section
    return None


def build_section_body(description: str, children: list[tuple[str, str]], news_cat_path: str | None) -> str:
    """Build HTML body for a hub section page."""
    links = "\n".join(
        f'    <li><a href="{href}">{label}</a></li>'
        for label, href in children
    )
    body = (
        f'<p class="section-intro">{description}</p>\n'
        f'<ul class="section-nav">\n{links}\n</ul>'
    )
    if news_cat_path:
        body += (
            f'\n\n<div class="section-news-link">'
            f'<a href="/{news_cat_path}/" class="btn btn--primary">'
            f"Переглянути всі новини за цим напрямом →</a></div>"
        )
    return body


def _news_admin_url(menu_path: str) -> str | None:
    cat_path = news_category_for_menu_path(menu_path)
    if not cat_path:
        return None
    try:
        from apps.news.models import Category
        cat = Category.objects.get(path=cat_path, is_active=True)
        return f"/admin/news/article/?category={cat.pk}"
    except Exception:
        return f"/admin/news/article/?category__path={cat_path}"


def _category_for_page(url_path: str):
    """News category tied to this menu URL, if any."""
    from apps.news.models import Category

    clean = _normalize_path(url_path)
    for path in (clean, news_category_for_menu_path(clean)):
        if not path:
            continue
        try:
            return Category.objects.get(path=path, is_active=True)
        except Category.DoesNotExist:
            continue
    return None


def _article_admin_url(article) -> str:
    return reverse("admin:news_article_change", args=[article.pk])


def _category_landing_slugs(category) -> set[str]:
    path_leaf = category.path.rsplit("/", 1)[-1]
    return {path_leaf, category.alias}


def _articles_for_category_panel(category):
    from apps.news.models import Article

    skip = _category_landing_slugs(category)
    return (
        Article.objects.filter(category=category, is_published=True)
        .exclude(slug__in=skip)
        .order_by("title", "-published_at")
    )


def admin_edit_url_for_href(href: str) -> str:
    """Resolve a public href (article .html or menu path) to an admin edit URL."""
    clean_href = href.strip()
    if not clean_href.startswith("/"):
        clean_href = f"/{clean_href}"

    match = _ARTICLE_HREF_RE.match(clean_href)
    if match:
        from apps.news.models import Article

        jid = int(match.group("jid"))
        slug = match.group("slug")
        art = (
            Article.objects.filter(joomla_id=jid, is_published=True).first()
            or Article.objects.filter(slug=slug, is_published=True).first()
        )
        if art:
            return _article_admin_url(art)

    return admin_edit_url_for_path(clean_href.rstrip("/"))


def _links_from_body(body: str) -> list[tuple[str, str]]:
    """Extract internal navigation links from a link-list style body."""
    if not body or ("<ul" not in body and "<ol" not in body):
        return []
    links: list[tuple[str, str]] = []
    seen: set[str] = set()
    for href, label in _BODY_LINK_RE.findall(body):
        href = href.strip()
        if not href.startswith("/") or href.startswith("//"):
            continue
        label = re.sub(r"\s+", " ", label).strip()
        if not label or href in seen:
            continue
        seen.add(href)
        links.append((label, href))
    return links


def page_content_links(url_path: str, body: str = "") -> list[tuple[str, str]]:
    """Admin (label, url) pairs for pages managed via sub-items, not body editor."""
    links: list[tuple[str, str]] = []

    hub = hub_info_for(url_path)
    if hub:
        for label, href in hub.get("children", []):
            links.append((label, admin_edit_url_for_path(href)))
        news_cat = hub.get("news_category_path")
        if news_cat:
            from apps.news.models import Category

            try:
                cat = Category.objects.get(path=news_cat, is_active=True)
                links.append(
                    ("Новини цього розділу", f"/admin/news/article/?category={cat.pk}")
                )
            except Category.DoesNotExist:
                links.append(
                    ("Новини цього розділу", f"/admin/news/article/?category__path={news_cat}")
                )
        return links

    category = _category_for_page(url_path)
    if category is not None:
        articles = _articles_for_category_panel(category)
        if articles.exists():
            return [(art.title, _article_admin_url(art)) for art in articles]

    menu_news = news_category_for_menu_path(_normalize_path(url_path))
    if menu_news:
        from apps.news.models import Category

        try:
            cat = Category.objects.get(path=menu_news, is_active=True)
            return [("Новини цього розділу", f"/admin/news/article/?category={cat.pk}")]
        except Category.DoesNotExist:
            return [("Новини цього розділу", f"/admin/news/article/?category__path={menu_news}")]

    for label, href in _links_from_body(body):
        links.append((label, admin_edit_url_for_href(href)))
    return links


def uses_content_panel(url_path: str, body: str = "") -> bool:
    return bool(page_content_links(url_path, body))


def article_content_links(article) -> list[tuple[str, str]]:
    """Admin links for index/list articles — body links or category siblings."""
    body_links = _links_from_body(article.body or "")
    if body_links:
        return [(label, admin_edit_url_for_href(href)) for label, href in body_links]

    category = article.category
    if category is None:
        return []

    skip = _category_landing_slugs(category)
    if article.slug in skip:
        siblings = _articles_for_category_panel(category)
        return [(s.title, _article_admin_url(s)) for s in siblings]

    return []


def article_uses_content_panel(article) -> bool:
    return bool(article_content_links(article))


def render_admin_content_panel(links: list[tuple[str, str]]) -> str:
    from django.utils.html import format_html
    from django.utils.safestring import mark_safe

    if not links:
        return "—"

    link_style = (
        "display:flex;align-items:center;justify-content:space-between;"
        "padding:10px 14px;margin-bottom:8px;border-radius:8px;"
        "background:#1e293b;border:1px solid #334155;text-decoration:none;"
        "color:#e2e8f0;font-weight:500;"
    )
    items = [
        format_html(
            '<a href="{url}" style="{style}">'
            "<span>{label}</span>"
            '<span style="color:#38bdf8;font-size:0.85rem;">Редагувати →</span>'
            "</a>",
            url=admin_url,
            style=link_style,
            label=label,
        )
        for label, admin_url in links
    ]
    return mark_safe("".join(items))


def admin_edit_url_for_path(path: str) -> str:
    """Resolve a public site path to the matching admin edit/list URL."""
    href = path if path.startswith("/") else f"/{path}"
    clean = href.strip("/")

    if clean.startswith("documents/"):
        slug = clean.removeprefix("documents/")
        return (
            reverse("admin:documents_documentcategory_go")
            + "?"
            + urlencode({"slug": slug})
        )
    if clean == "documents":
        return "/admin/documents/documentcategory/"

    if clean.startswith("gallery"):
        return "/admin/gallery/galleryalbum/"

    if clean == "materiali":
        return "/admin/news/article/"

    news_url = _news_admin_url(clean)
    if news_url:
        return news_url

    return reverse("admin:pages_staticpage_go") + "?" + urlencode({"path": href.rstrip("/")})
