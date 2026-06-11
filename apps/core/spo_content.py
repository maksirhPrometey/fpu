"""Static SPO homepage content aligned with spo.fpsu.org.ua."""

from __future__ import annotations

from typing import TypedDict


class SpoMember(TypedDict):
    title: str
    url: str
    external: bool


SPO_HERO_LEAD = (
    "СПІЛЬНИЙ ПРЕДСТАВНИЦЬКИЙ ОРГАН РЕПРЕЗЕНТАТИВНИХ ВСЕУКРАЇНСЬКИХ "
    "ОБ'ЄДНАНЬ ПРОФСПІЛОК НА НАЦІОНАЛЬНОМУ РІВНІ є стороною соціального "
    "діалогу на національному рівні, який:"
)

SPO_HERO_POINTS: tuple[str, ...] = (
    (
        "Представляє інтереси понад 5,2 мільйонів працівників всіх секторів "
        "економіки та сфер суспільного життя у заходах на національному та "
        "міжнародному рівнях"
    ),
    (
        "Є учасником колективних переговорів з укладення Генеральної угоди, "
        "реалізації та контролю за її виконанням"
    ),
    (
        "Представляє і захищає права та інтереси працівників під час розробки "
        "нормативно-правових актів у сфері трудових та соціально-економічних "
        "відносин."
    ),
)

SPO_SUBJECTS_URL = (
    "https://spo.fpsu.org.ua/subyekty-ugody-pro-utvorennya-spo-obyednan-profspilok/"
)

SPO_MEMBERS: tuple[SpoMember, ...] = (
    {"title": "Федерація профспілок України", "url": "/", "external": False},
    {
        "title": "Федерація профспілок транспортників України",
        "url": "https://zalp.org.ua/",
        "external": True,
    },
    {
        "title": "Конфедерація Вільних профспілок України",
        "url": "https://kvpu.org.ua/",
        "external": True,
    },
    {
        "title": "Об'єднання всеукраїнських профспілок і профоб'єднань «Єдність»",
        "url": SPO_SUBJECTS_URL,
        "external": True,
    },
    {
        "title": "Об'єднання всеукраїнських автономних профспілок",
        "url": SPO_SUBJECTS_URL,
        "external": True,
    },
)

SPO_NEWS_ALL_URL = "/spo-ob-iednan-profspilok/novyny/"

SPO_WP_CATEGORY_PATH = "spo-wp-novyny"
