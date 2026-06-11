"""Joomla /documents URL aliases and legacy path mapping."""
from __future__ import annotations

# /documents/<slug>/ aliases → canonical DocumentCategory.slug
SLUG_ALIASES: dict[str, str] = {
    "materiali-vii-zizdu-fpu": "materialy-vii-zyizdu-fpu",
    "materiali-viii-zizdu-fpu": "materialy-viii-zyizdu-fpu",
    "strategiya-diyalnosti-fpu": "strategiya-diyalnosti-fpu-2021-2026",
    "materiali-vii-z-jizdu-federatsiji-profspilok-ukrajini": "materialy-vii-zyizdu-fpu",
    "materiali-viii-z-jizdu-federatsiji-profspilok-ukrajini": "materialy-viii-zyizdu-fpu",
    "reprezentatyvnist": "reprezentativnist",
    "stratehiia-diialnosti-fpu-na-2021-2026-roky": "strategiya-diyalnosti-fpu-2021-2026",
    "postanovi-rad-fpu": "postanovi-radi-fpu",
}

STRATEGY_SLUGS = frozenset({"strategiya-diyalnosti-fpu", "strategiya-diyalnosti-fpu-2021-2026"})


def resolve_category_slug(slug: str) -> str:
    return SLUG_ALIASES.get(slug.strip("/"), slug.strip("/"))
