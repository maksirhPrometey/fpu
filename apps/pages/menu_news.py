"""Menu StaticPage URL → news Category path (Joomla blog layout aliases)."""
from __future__ import annotations

# Ключ — шлях меню (без початкового /), значення — path категорії новин у БД.
MENU_TO_NEWS_CATEGORY: dict[str, str] = {
    "pro-fpu/zakonodavche-regulyuvannya-diyalnosti-profspilok": (
        "informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist"
    ),
    "napryamki-diyalnosti/pravovij-zakhist": (
        "informatsiya-za-napryamkami-diyalnosti/pravovij-zakhist"
    ),
    "napryamki-diyalnosti/okhorona-pratsi-i-zdorov-ya": (
        "informatsiya-za-napryamkami-diyalnosti/okhorona-pratsi-i-zdorov-ya"
    ),
    "napryamki-diyalnosti/sotsialnij-zakhist": (
        "informatsiya-za-napryamkami-diyalnosti/sotsialnij-zakhist"
    ),
    "napryamki-diyalnosti/virobnicha-politika-ta-tsinoutvorennya": (
        "informatsiya-za-napryamkami-diyalnosti/vyrobnycha-polityka-ta-tsinoutvorennia"
    ),
    "napryamki-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya": (
        "informatsiya-za-napryamkami-diyalnosti/sotsialne-strakhuvannya-i-pensijne-zabezpechennya"
    ),
    "napryamki-diyalnosti/sotsialnij-dialog-ta-kolektivno-dogovirne-regulyuvannya": (
        "informatsiya-za-napryamkami-diyalnosti/sotsialnij-dialog"
    ),
    "napryamki-diyalnosti/organizatsijna-robota": (
        "informatsiya-za-napryamkami-diyalnosti/organizatsionnaya-rabota"
    ),
    "napryamki-diyalnosti/molodizhna-politika": (
        "informatsiya-za-napryamkami-diyalnosti/molodizhna-politika"
    ),
    "napryamki-diyalnosti/informatsijna-robota": (
        "informatsiya-za-napryamkami-diyalnosti/informatsijna-robota"
    ),
    "napryamki-diyalnosti/mizhnarodna-robota": (
        "informatsiya-za-napryamkami-diyalnosti/mizhnarodna-robota"
    ),
}


def news_category_for_menu_path(menu_path: str) -> str | None:
    return MENU_TO_NEWS_CATEGORY.get(menu_path.strip("/"))
