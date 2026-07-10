"""Core views — home, search, contact, joomla legacy redirects."""
from __future__ import annotations

from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import HttpRequest, HttpResponse, HttpResponsePermanentRedirect
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from apps.core.models import ContactMessage, JoinRequest, MemOrgPage, PageSection, Priority, SiteSettings, TeamMember
from apps.core.utils import default_articles, default_priorities, default_team_members
from apps.core.youtube import get_hero_videos
from apps.news.models import Article
from apps.pages.models import StaticPage


@require_GET
def home(request: HttpRequest) -> HttpResponse:
    from apps.news.models import Category as _NewsCategory

    articles_qs = (
        Article.objects.filter(is_published=True)
        .select_related("category")
        .order_by("-published_at")[:13]
    )
    articles = list(articles_qs)
    if not articles:
        articles = default_articles()

    # ── Hero: збираємо список [lead, slide1, slide2, slide3, slide4, …решта] ──
    def _fetch(pk: int | None) -> Article | None:
        if not pk:
            return None
        return (
            Article.objects.filter(pk=pk, is_published=True)
            .select_related("category")
            .first()
        )

    try:
        _cfg = SiteSettings.get()
        pinned_lead   = _fetch(_cfg.hero_lead_article_id)
        pinned_slides = [
            a for a in (
                _fetch(_cfg.hero_slide_1_id),
                _fetch(_cfg.hero_slide_2_id),
                _fetch(_cfg.hero_slide_3_id),
                _fetch(_cfg.hero_slide_4_id),
            ) if a
        ]
    except Exception:
        pinned_lead, pinned_slides = None, []

    # Якщо жодне поле не заповнене — авто з категорії "Головна новина"
    if not pinned_lead and not pinned_slides:
        try:
            holovna_cat = _NewsCategory.objects.get(path="holovna-novyna", is_active=True)
            featured = list(
                Article.objects.filter(category=holovna_cat, is_published=True)
                .select_related("category")
                .order_by("-published_at")[:5]
            )
            if featured:
                featured_ids = {a.pk for a in featured}
                rest = [a for a in articles if a.pk not in featured_ids]
                articles = (featured + rest)[:13]
        except Exception:
            pass
    else:
        # Формуємо список: lead + slides + решта (без дублів)
        pinned_ids = {a.pk for a in [pinned_lead] + pinned_slides if a}
        rest = [a for a in articles if a.pk not in pinned_ids]
        lead = pinned_lead or (pinned_slides[0] if pinned_slides else articles[0] if articles else None)
        slides = pinned_slides if pinned_slides else []
        articles = ([lead] if lead else []) + slides + rest
        articles = [a for a in articles if a][:13]

    priorities_qs = Priority.objects.filter(is_active=True).order_by("order")
    priorities = list(priorities_qs)
    if not priorities:
        priorities = default_priorities()

    team_qs = TeamMember.objects.filter(is_active=True).order_by("order")
    team_members = list(team_qs) or default_team_members()

    home_sections = {
        s.section_type: s
        for s in PageSection.objects.filter(page="home", is_active=True).order_by("order")
    }

    # "Останні новини" — завжди суто за датою, незалежно від hero-логіки
    latest_articles = list(
        Article.objects.filter(is_published=True)
        .select_related("category")
        .order_by("-published_at")[:6]
    )

    context = {
        "articles": articles,
        "latest_articles": latest_articles,
        "priorities": priorities,
        "team_members": team_members,
        "hero_section": home_sections.get("hero"),
        "announce_section": home_sections.get("announce"),
        "hero_videos": get_hero_videos(),
    }
    return render(request, "core/home.html", context)


@require_GET
def search(request: HttpRequest) -> HttpResponse:
    """Full-text search across articles and static pages."""
    query = request.GET.get("q", "").strip()
    page_num = request.GET.get("page", 1)
    results = []
    total = 0

    if query:
        article_qs = (
            Article.objects.filter(is_published=True)
            .filter(
                Q(title__icontains=query)
                | Q(summary__icontains=query)
                | Q(body__icontains=query)
            )
            .order_by("-published_at")
            .select_related("category")
        )
        page_qs = (
            StaticPage.objects.filter(is_published=True)
            .filter(Q(title__icontains=query) | Q(body__icontains=query))
        )

        # Об'єднуємо результати (articles пріоритетніші)
        combined = list(article_qs[:100]) + list(page_qs[:20])
        total = len(combined)
        paginator = Paginator(combined, 20)
        results = paginator.get_page(page_num)

    canonical = request.build_absolute_uri("/search/")
    context = {
        "query": query,
        "results": results,
        "total": total,
        "page_meta_title": (_("Пошук") + f": {query}") if query else _("Пошук"),
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Пошук"), "url": "/search/"},
        ],
    }
    return render(request, "core/search.html", context)


@require_http_methods(["GET", "POST"])
def contact(request: HttpRequest) -> HttpResponse:
    """Contact form — sends email via SMTP."""
    settings_obj = SiteSettings.get()
    success = False
    errors: dict[str, str] = {}
    form_data: dict = {}

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        subject = request.POST.get("subject", "").strip()
        message = request.POST.get("message", "").strip()

        # Проста валідація
        if not name:
            errors["name"] = _("Введіть ваше ім'я")
        if not email or "@" not in email:
            errors["email"] = _("Введіть коректний email")
        if not subject:
            errors["subject"] = _("Введіть тему")
        if not message or len(message) < 10:
            errors["message"] = _("Повідомлення надто коротке")

        form_data = {"name": name, "email": email, "subject": subject, "message": message}

        if not errors:
            # Rate limit — простий cache-based (5 запитів/год з IP)
            ip = request.META.get("REMOTE_ADDR", "unknown")
            from django.core.cache import cache as django_cache
            rate_key = f"contact_rate_{ip}"
            count = django_cache.get(rate_key, 0)
            if count >= 5:
                errors["__all__"] = _("Забагато запитів. Спробуйте пізніше.")
            else:
                django_cache.set(rate_key, count + 1, 3600)
                try:
                    ContactMessage.objects.create(
                        name=name,
                        email=email,
                        subject=subject,
                        message=message,
                        ip_address=ip or None,
                    )
                    send_mail(
                        subject=f"[ФПУ] {subject} — від {name}",
                        message=f"Від: {name} <{email}>\n\n{message}",
                        from_email=settings_obj.contact_email or "noreply@fpsu.org.ua",
                        recipient_list=[settings_obj.contact_email or "fpsu@fpsu.org.ua"],
                        fail_silently=True,
                    )
                    success = True
                    form_data = {}
                except Exception:
                    errors["__all__"] = _("Помилка відправки. Спробуйте пізніше або зателефонуйте.")

    canonical = request.build_absolute_uri("/contacts/")
    context = {
        "success": success,
        "errors": errors,
        "form_general_error": errors.get("__all__", ""),
        "form_data": form_data,
        "site_settings": settings_obj,
        "page_meta_title": _("Контакти"),
        "page_meta_description": _("Контакти Федерації профспілок України: адреса, телефон, форма зворотного зв'язку."),
        "canonical_url": canonical,
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Контакти"), "url": "/contacts/"},
        ],
    }
    return render(request, "core/contact.html", context)


@require_GET
def spo_page(request: HttpRequest) -> HttpResponse:
    """СПО об'єднань профспілок — mirror of spo.fpsu.org.ua homepage."""
    import urllib.error

    from django.utils import timezone

    from apps.core.models import SpoHomeCache
    from apps.core.spo_content import (
        SPO_HERO_LEAD,
        SPO_HERO_POINTS,
        SPO_MEMBERS,
        SPO_NEWS_ALL_URL,
    )
    from apps.core.spo_live_sync import fetch_spo_homepage
    from apps.news.models import Article
    from apps.core.youtube import extract_youtube_id, youtube_embed_url, youtube_watch_url

    cache = SpoHomeCache.load()
    if not cache.videos and not cache.gallery:
        try:
            data = fetch_spo_homepage()
            cache.news = data["news"]
            cache.videos = data["videos"]
            cache.gallery = data["gallery"]
            cache.partners = data["partners"]
            cache.synced_at = timezone.now()
            cache.save()
        except (urllib.error.URLError, TimeoutError, OSError):
            pass

    wp_articles = list(
        Article.objects.filter(is_published=True, is_spo=True)
        .select_related("category")
        .order_by("-published_at")[:3]
    )
    if wp_articles:
        spo_news = [
            {
                "date": article.display_date,
                "url": article.get_absolute_url(),
                "title": article.title,
                "excerpt": article.listing_excerpt,
                "image_url": article.listing_image_url or article.image_url,
            }
            for article in wp_articles
        ]
    else:
        spo_news = cache.news

    videos: list[dict] = []
    for video in cache.videos:
        video_id = extract_youtube_id(video.get("embed_url", ""))
        if video_id:
            videos.append({
                **video,
                "embed_url": youtube_embed_url(video_id),
                "watch_url": video.get("watch_url") or youtube_watch_url(video_id),
            })
        else:
            videos.append(video)

    context = {
        "spo_hero_lead": SPO_HERO_LEAD,
        "spo_hero_points": SPO_HERO_POINTS,
        "spo_members": SPO_MEMBERS,
        "spo_news": spo_news,
        "spo_videos": videos,
        "spo_gallery": cache.gallery,
        "spo_partners": cache.partners,
        "spo_news_all_url": SPO_NEWS_ALL_URL,
        "page_meta_title": "СПО об'єднань профспілок",
        "page_meta_description": (
            "Спільний представницький орган репрезентативних всеукраїнських "
            "об'єднань профспілок на національному рівні."
        ),
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "СПО об'єднань профспілок", "url": "/spo-ob-iednan-profspilok/"},
        ],
    }
    return render(request, "core/spo.html", context)


_SPO_NEWS_PAGE_SIZE = 10


@require_GET
def spo_news_list(request: HttpRequest) -> HttpResponse:
    """All SPO blog posts imported from spo.fpsu.org.ua."""
    from apps.news.models import Article

    qs = (
        Article.objects.filter(is_published=True, is_spo=True)
        .select_related("category")
        .order_by("-published_at")
    )
    paginator = Paginator(qs, _SPO_NEWS_PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    context = {
        "articles": list(page_obj.object_list),
        "page_obj": page_obj,
        "page_meta_title": "Новини СПО",
        "page_meta_description": "Новини Спільного представницького органу об'єднань профспілок.",
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "СПО об'єднань профспілок", "url": "/spo-ob-iednan-profspilok/"},
            {"title": "Новини", "url": "/spo-ob-iednan-profspilok/novyny/"},
        ],
    }
    return render(request, "core/spo_news_list.html", context)


@require_GET
def spo_news_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Single SPO blog post."""
    from apps.news.models import Article

    article = get_object_or_404(
        Article,
        slug=slug,
        is_spo=True,
        is_published=True,
    )
    canonical = request.build_absolute_uri(article.get_absolute_url())
    context = {
        "article": article,
        "category": article.category,
        "page_meta_title": article.effective_meta_title,
        "page_meta_description": article.meta_description or article.summary,
        "page_meta_keywords": article.meta_keywords,
        "canonical_url": canonical,
        "og_image": article.image_url,
        "og_type": "article",
        "breadcrumbs": [
            {"title": "Головна", "url": "/"},
            {"title": "СПО об'єднань профспілок", "url": "/spo-ob-iednan-profspilok/"},
            {"title": "Новини", "url": "/spo-ob-iednan-profspilok/novyny/"},
            {"title": article.title, "url": article.get_absolute_url()},
        ],
    }
    return render(request, "news/article_detail.html", context)


_BASE = "https://www.fpsu.org.ua/sajty-chlenskikh-organizatsij-2/2012-12-10-16-02-20"
_GALUZEVI_LEGACY: list[dict] = [
    {"name": "Професійна спілка працівників авіабудування та машинобудування України",
     "url": f"{_BASE}/195-profspilka-aviabudivnikiv-ukrajini.html"},
    {"name": "Профспілка авіапрацівників України",
     "url": f"{_BASE}/194-profspilka-aviapratsivnikiv-ukrajini.html"},
    {"name": "Профспілка працівників автомобільного транспорту та шляхового господарства України",
     "url": f"{_BASE}/193-profspilka-pratsivnikiv-avtomobilnogo-transportu-ta-shlyakhovogo-gospodarstva-ukrajini.html"},
    {"name": "Профспілка працівників автомобільного та сільськогосподарського машинобудування України",
     "url": f"{_BASE}/192-profspilka-pratsivnikiv-avtomobilnogo-ta-silskogospodarskogo-mashinobuduvannya-ukrajini.html"},
    {"name": "Профспілка працівників агропромислового комплексу України",
     "url": "https://profapk.org.ua/"},
    {"name": "Всеукраїнська профспілка адвокатів України",
     "url": f"{_BASE}/25246-vseukrainska-profspilka-advokativ-ukrainy.html"},
    {"name": "Атомпрофспілка — Профспілка працівників атомної енергетики та промисловості України",
     "url": "https://www.atomprofspilka.info/"},
    {"name": "ПРОФБУД — Профспілка працівників будівництва і промисловості будівельних матеріалів України",
     "url": "https://www.profbud.org.ua/"},
    {"name": "Всеукраїнська професійна спілка працівників банківських і фінансових установ",
     "url": f"{_BASE}/25247-vseukrainska-profesiina-spilka-pratsivnykiv-bankivskykh-i-finansovykh-ustanov.html"},
    {"name": "Всеукраїнська профспілка виробничників, підприємців та трудових мігрантів",
     "url": f"{_BASE}/188-vseukrajinska-profspilka-virobnichnikiv-i-pidpriemtsiv-ukrajini.html"},
    {"name": "Профспілка працівників вугільної промисловості України",
     "url": "http://www.prupu.org/"},
    {"name": "Профспілка працівників газових господарств України",
     "url": f"{_BASE}/186-profspilka-pratsivnikiv-gazovikh-gospodarstv-ukrajini.html"},
    {"name": "Професійна спілка працівників геології, геодезії та картографії України",
     "url": f"{_BASE}/185-profesijna-spilka-pratsivnikiv-geologiji-geodeziji-ta-kartografiji-ukrajini.html"},
    {"name": "Професійна спілка працівників державних установ України",
     "url": "http://ppdu-ua.org/"},
    {"name": "УКРЕЛЕКТРОПРОФСПІЛКА — Профспілка працівників енергетики та електротехнічної промисловості України",
     "url": "http://ukrelectroprofspilka.org.ua"},
    {"name": "Профспілка працівників житлово-комунального господарства, місцевої промисловості та побутового обслуговування України",
     "url": f"{_BASE}/182-profspilka-pratsivnikiv-zhitlovo-komunalnogo-gospodarstva-mistsevoji-promislovosti-pobutovogo-obslugovuvannya-naselennya-ukrajini.html"},
    {"name": "Профспілка працівників зв'язку України",
     "url": "https://profzviazku.org.ua/"},
    {"name": "Всеукраїнська профспілка працівників інноваційних і малих підприємств",
     "url": f"{_BASE}/180-vseukrajinska-profspilka-pratsivnikiv-innovatsijnikh-i-malikh-pidpriemstv.html"},
    {"name": "Професійна спілка працівників космічного та загального машинобудування України",
     "url": f"{_BASE}/179-profesijna-spilka-pratsivnikiv-kosmichnogo-ta-zagalnogo-mashinobuduvannya-ukrajini.html"},
    {"name": "Професійна спілка працівників культури України",
     "url": "https://cultura.fpsu.org.ua/"},
    {"name": "Профспілка працівників лісових галузей України",
     "url": f"{_BASE}/177-profspilka-pratsivnikiv-lisovikh-galuzej-ukrajini.html"},
    {"name": "Професійна спілка працівників лісового господарства України",
     "url": f"{_BASE}/176-profesijna-spilka-pratsivnikiv-lisovogo-gospodarstva-ukrajini.html"},
    {"name": "Профспілка машинобудівників та приладобудівників України",
     "url": f"{_BASE}/175-profspilka-mashinobudivnikiv-ta-priladobudivnikiv-ukrajini.html"},
    {"name": "Професійна спілка працівників машинобудування та металообробки України",
     "url": f"{_BASE}/174-profesijna-spilka-pratsivnikiv-mashinobuduvannya-ta-metaloobrobki-ukrajini.html"},
    {"name": "ПМГУ — Профспілка металургів і гірників України",
     "url": "http://www.pmguinfo.dp.ua/"},
    {"name": "Професійна спілка працівників молодіжних житлових комплексів та комітетів місцевого самоврядування України",
     "url": f"{_BASE}/172-profesijna-spilka-pratsivnikiv-molodizhnikh-zhitlovikh-kompleksiv-ta-komitetiv-mistsevogo-samovryaduvannya-ukrajini.html"},
    {"name": "Професійна спілка робітників морського транспорту України",
     "url": f"{_BASE}/171-profesijna-spilka-robitnikiv-morskogo-transportu-ukrajini.html"},
    {"name": "Укрнафтогазпрофспілка — Профспілка працівників нафтової і газової промисловості України",
     "url": "https://ngpu.org.ua/"},
    {"name": "Профспілка працівників оборонної промисловості України",
     "url": f"{_BASE}/169-profspilka-pratsivnikiv-oboronnoji-promislovosti-ukrajini.html"},
    {"name": "Профспілка працівників освіти і науки України",
     "url": "https://www.pon.org.ua/"},
    {"name": "Профспілка працівників охорони здоров'я України",
     "url": "https://medprof.org.ua/"},
    {"name": "Професійна спілка працівників Пенсійного фонду України",
     "url": f"{_BASE}/166-profesijna-spilka-pratsivnikiv-pensijnogo-fondu-ukrajini.html"},
    {"name": "Професійна спілка працівників радіоелектроніки та машинобудування України",
     "url": f"{_BASE}/164-profesijna-spilka-pratsivnikiv-radioelektroniki-ta-mashinobuduvannya-ukrajini.html"},
    {"name": "Профспілка працівників рибного господарства України",
     "url": f"{_BASE}/163-profspilka-pratsivnikiv-ribnogo-gospodarstva-ukrajini.html"},
    {"name": "Українська профспілка працівників річкового транспорту",
     "url": f"{_BASE}/162-ukrajinska-profesijna-spilka-pratsivnikiv-richkovogo-transportu.html"},
    {"name": "Профспілка працівників соціальної сфери України",
     "url": f"{_BASE}/161-profspilka-pratsivnikiv-sotsialnoji-sferi-ukrajini.html"},
    {"name": "Профспілка працівників споживчої кооперації України",
     "url": f"{_BASE}/160-profspilka-pratsivnikiv-spozhivchoji-kooperatsiji-ukrajini.html"},
    {"name": "Всеукраїнська профспілка захисників України, спортсменів та працівників сфери фізичної культури",
     "url": f"{_BASE}/23108-vseukrajinska-profspilka-sportsmeniv-pratsivnikiv-sfer-fizichnoji-kulturi-i-sportu-molodizhnoji-politiki-ta-natsionalno-patriotichnogo-vikhovannya.html"},
    {"name": "Професійна спілка працівників суднобудування України",
     "url": f"{_BASE}/159-profesijna-spilka-pratsivnikiv-sudnobuduvannya-ukrajini.html"},
    {"name": "Професійна спілка таксистів України",
     "url": f"{_BASE}/158-profesijna-spilka-taksistiv-ukrajini.html"},
    {"name": "Профспілка працівників текстильної та легкої промисловості України",
     "url": f"{_BASE}/157-profspilka-pratsivnikiv-tekstilnoji-ta-legkoji-promislovosti-ukrajini.html"},
    {"name": "Всеукраїнська профспілка працівників і підприємців торгівлі, громадського харчування та послуг",
     "url": f"{_BASE}/156-vseukrajinska-profspilka-pratsivnikiv-i-pidpriemtsiv-torgivli-gromadskogo-kharchuvannya-ta-poslug-vseukrajinska-profspilka-torgivli.html"},
    {"name": "Всеукраїнська незалежна профспілка працівників транспорту",
     "url": f"{_BASE}/155-vseukrajinska-nezalezhna-profspilka-pratsivnikiv-transportu.html"},
    {"name": "Всеукраїнська профспілка «Футбол України»",
     "url": f"{_BASE}/154-vseukrajinska-profesijna-spilka-futbol-ukrajini.html"},
    {"name": "Профспілка працівників хімічних та нафтохімічних галузей промисловості України",
     "url": "http://www.profchim.kiev.ua/"},
    {"name": "Українська федерація профспілкових організацій — профспілка підприємств з іноземними інвестиціями",
     "url": f"{_BASE}/25248-ukrainska-federatsiia-profspilkovykh-orhanizatsii-profspilka-pratsivnykiv-pidpryiemstv-z-inozemnymy-investytsiiamy-hospodarskykh-tovarystv-orhanizatsii-ta-ustanov.html"},
]

_TERYTORIALNI: list[dict] = [
    {"name": "Федерація профспілок Вінницької області",                   "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/222-federatsiya-profspilok-vinnitskoji-oblasti.html"},
    {"name": "Федерація профспілок Волинської області",                   "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/221-federatsiya-profspilok-volinskoji-oblasti.html"},
    {"name": "Дніпропетровське обласне об'єднання профспілок",            "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/220-dnipropetrovske-oblasne-ob-ednannya-profspilok.html"},
    {"name": "Донецька обласна рада професійних спілок",                  "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/219-donetska-oblasna-rada-profesijnikh-spilok.html"},
    {"name": "Федерація профспілок Житомирської області",                 "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/218-federatsiya-profspilok-zhitomirskoji-oblasti.html"},
    {"name": "Закарпатська обласна рада профспілок",                      "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/217-zakarpatska-oblasna-rada-profspilok.html"},
    {"name": "Запорізька обласна рада профспілок",                        "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/216-zaporizka-oblasna-rada-profspilok.html"},
    {"name": "Рада профспілок Івано-Франківської області",                "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/215-rada-profspilok-ivano-frankivskoji-oblasti.html"},
    {"name": "Київська міська рада профспілок",                           "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/214-kijivska-miska-rada-profspilok.html"},
    {"name": "Київська обласна рада професійних спілок",                  "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/213-kijivska-oblasna-rada-profesijnikh-spilok.html"},
    {"name": "Федерація профспілок Кіровоградської області",              "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/212-federatsiya-profspilok-kirovogradskoji-oblasti.html"},
    {"name": "Федерація незалежних профспілок Криму",                     "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/211-federatsiya-nezalezhnikh-profspilok-krimu.html"},
    {"name": "Федерація профспілок Луганської області",                   "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/210-federatsiya-profspilok-luganskoji-oblasti.html"},
    {"name": "Об'єднання профспілок Львівщини",                           "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/209-ob-ednannya-profspilok-lvivshchini.html"},
    {"name": "Миколаївська обласна рада профспілок",                      "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/208-mikolajivska-oblasna-rada-profspilok.html"},
    {"name": "Федерація профспілок Одеської області",                     "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/207-federatsiya-profspilok-odeskoji-oblasti.html"},
    {"name": "Полтавська обласна рада профспілок",                        "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/206-poltavska-oblasna-rada-profspilok.html"},
    {"name": "Федерація профспілок Рівненської області",                  "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/205-federatsiya-profspilok-rivnenskoji-oblasti.html"},
    {"name": "Сумська обласна рада професійних спілок",                   "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/204-sumska-oblasna-rada-profesijnikh-spilok.html"},
    {"name": "Тернопільська обласна рада профспілок",                     "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/203-ternopilska-oblasna-rada-profspilok.html"},
    {"name": "Об'єднання профспілок Харківської області",                 "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/202-ob-ednannya-profspilok-kharkivskoji-oblasti.html"},
    {"name": "Херсонська обласна міжгалузева рада профспілок",            "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/201-khersonska-oblasna-mizhgaluzeva-rada-profspilok.html"},
    {"name": "Федерація профспілок Хмельницької області",                 "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/200-federatsiya-profspilok-khmelnitskoji-oblasti.html"},
    {"name": "Федерація профспілок Черкаської області",                   "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/199-federatsiya-profspilok-cherkaskoji-oblasti.html"},
    {"name": "Чернівецька обласна рада профспілок",                       "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/198-chernivetska-oblasna-rada-profspilok.html"},
    {"name": "Федерація профспілкових організацій Чернігівської області", "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/197-federatsiya-profspilkovikh-organizatsij-chernigivskoji-oblasti.html"},
    {"name": "Севастопольська міська рада профспілок",                    "url": "https://www.fpsu.org.ua/pro-fpu/chlenski-organizatsiji/teritorialni-ob-ednannya-organizatsij-profspilok/196-sevastopolska-miska-rada-profspilok.html"},
]


@require_GET
def member_sites_page(request: HttpRequest) -> HttpResponse:
    """Сайти членських організацій ФПУ — дані з MemOrgPage (БД)."""
    galuzevi = list(
        MemOrgPage.objects.filter(org_type="sectoral", is_published=True).order_by("title")
    )
    terytorialni = list(
        MemOrgPage.objects.filter(org_type="regional", is_published=True).order_by("region", "title")
    )
    context = {
        "galuzevi": galuzevi,
        "terytorialni": terytorialni,
        "page_meta_title": _("Сайти членських організацій"),
        "page_meta_description": _(
            "Всеукраїнські галузеві профспілки та територіальні об'єднання "
            "організацій профспілок — членські організації Федерації профспілок України."
        ),
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Сайти членських організацій"), "url": "/sajty-chlenskykh-orhanizatsii/"},
        ],
    }
    return render(request, "core/member_sites.html", context)


@require_http_methods(["GET", "POST"])
def join_request_page(request: HttpRequest) -> HttpResponse:
    """Форма «Стати членом профспілки»."""
    # #region agent log
    import json as _j, time as _t
    try:
        with open("/Users/olegbonislavskyi/Sites/Профспілки/.cursor/debug-8dffc0.log", "a") as _f:
            _f.write(_j.dumps({"sessionId": "8dffc0", "timestamp": int(_t.time() * 1000), "location": "core/views.py:join_request_page", "message": "view reached", "data": {"method": request.method, "path": request.path}, "hypothesisId": "H1_H3", "runId": "run1"}) + "\n")
    except Exception: pass
    # #endregion
    success = False
    errors: dict[str, str] = {}
    form_data: dict = {}

    if request.method == "POST":
        name      = request.POST.get("name", "").strip()
        email     = request.POST.get("email", "").strip()
        phone     = request.POST.get("phone", "").strip()
        workplace = request.POST.get("workplace", "").strip()
        profession = request.POST.get("profession", "").strip()
        message   = request.POST.get("message", "").strip()

        if not name:
            errors["name"] = _("Введіть ваше повне ім'я")
        if not email or "@" not in email:
            errors["email"] = _("Введіть коректний email")

        form_data = {
            "name": name, "email": email, "phone": phone,
            "workplace": workplace, "profession": profession, "message": message,
        }

        if not errors:
            ip = request.META.get("REMOTE_ADDR", "")
            JoinRequest.objects.create(
                name=name, email=email, phone=phone,
                workplace=workplace, profession=profession, message=message,
                ip_address=ip or None,
            )
            success = True
            form_data = {}

    context = {
        "success": success,
        "errors": errors,
        "form_data": form_data,
        "page_meta_title": _("Стати членом профспілки"),
        "page_meta_description": _(
            "Подайте заявку на вступ до профспілки. "
            "Федерація профспілок України захищає права і інтереси працівників."
        ),
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Напрями діяльності"), "url": "/napryamki-diyalnosti/"},
            {"title": _("Стати членом профспілки"), "url": "/staty-chlenom-profspilky/"},
        ],
    }
    return render(request, "core/join.html", context)


@require_GET
def mem_org_detail(request: HttpRequest, slug: str) -> HttpResponse:
    """Детальна сторінка членської організації."""
    org = get_object_or_404(MemOrgPage, slug=slug, is_published=True)
    context = {
        "org": org,
        "page_meta_title": org.title,
        "page_meta_description": org.meta_description or org.description[:160],
        "canonical_url": request.build_absolute_uri(org.get_absolute_url()),
        "breadcrumbs": [
            {"title": _("Головна"), "url": "/"},
            {"title": _("Членські організації"), "url": "/sajty-chlenskykh-orhanizatsii/"},
            {"title": org.short_name or org.title, "url": org.get_absolute_url()},
        ],
    }
    return render(request, "core/mem_org_detail.html", context)


@require_GET
def joomla_redirect(request: HttpRequest) -> HttpResponsePermanentRedirect:
    """301-редирект для старих Joomla index.php URL.

    Підтримувані формати:
      ?option=com_content&view=article&id=118:rada&catid=...  → article
      ?option=com_content&view=category&...&id=<catid>        → homepage fallback
      ?option=com_search&...                                   → /search/
      ?option=com_contact&...                                  → /contacts/
      все інше                                                 → /
    """
    params = request.GET
    option = params.get("option", "")
    view   = params.get("view", "")

    # ── com_search → search page ──────────────────────────────────────────────
    if option == "com_search":
        q = params.get("searchword", params.get("q", ""))
        return HttpResponsePermanentRedirect(f"/search/?q={q}" if q else "/search/")

    # ── com_contact → contacts page ───────────────────────────────────────────
    if option == "com_contact":
        return HttpResponsePermanentRedirect("/contacts/")

    # ── com_content, view=article ─────────────────────────────────────────────
    if option == "com_content" and view == "article":
        raw_id = params.get("id", "")
        joomla_id = _parse_joomla_id(raw_id)
        if joomla_id:
            try:
                article = Article.objects.get(joomla_id=joomla_id, is_published=True)
                return HttpResponsePermanentRedirect(article.get_absolute_url())
            except Article.DoesNotExist:
                pass
            # Спробуємо StaticPage по joomla_id у url_path
            try:
                page = StaticPage.objects.filter(
                    url_path__contains=f"{joomla_id}-"
                ).first()
                if page:
                    return HttpResponsePermanentRedirect(page.url_path.removesuffix(".html"))
            except Exception:
                pass

    # ── com_content, view=category → спробуємо знайти по префіксу шляху ──────
    if option == "com_content" and view in ("category", "section"):
        prefix = _path_prefix(request.path)
        if prefix:
            page = StaticPage.objects.filter(
                url_path__startswith=prefix, is_published=True
            ).first()
            if page:
                url = page.url_path.replace(".html", "")
                return HttpResponsePermanentRedirect(url)

    # ── fallback — homepage ───────────────────────────────────────────────────
    return HttpResponsePermanentRedirect("/")


def _parse_joomla_id(raw: str) -> int | None:
    """Parse joomla_id from '118:rada', '118-rada' or '118'."""
    if not raw:
        return None
    for sep in (":", "-"):
        if sep in raw:
            try:
                return int(raw.split(sep)[0])
            except ValueError:
                return None
    try:
        return int(raw)
    except ValueError:
        return None


def _path_prefix(path: str) -> str:
    """Return leading section from path, e.g. '/pro-fpu/index.php' → '/pro-fpu'."""
    parts = [p for p in path.rstrip("/").split("/") if p and p != "index.php"]
    return "/" + "/".join(parts) if parts else ""
