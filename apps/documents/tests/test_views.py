"""Documents views tests."""
from __future__ import annotations

import pytest
from django.urls import reverse

from apps.documents.models import Document, DocumentCategory


@pytest.fixture
def category(db):
    return DocumentCategory.objects.create(
        title="Постанови Ради ФПУ",
        slug="postanovi-radi-fpu",
        order=1,
    )


@pytest.fixture
def document(category):
    return Document.objects.create(
        title="Тестовий документ 2024",
        category=category,
        file_type="pdf",
        is_published=True,
    )


@pytest.mark.django_db
def test_document_index_200(client):
    response = client.get(reverse("documents:document_index"))
    assert response.status_code == 200


@pytest.mark.django_db
def test_document_index_shows_category(client, category):
    response = client.get(reverse("documents:document_index"))
    assert category.title.encode() in response.content


@pytest.mark.django_db
def test_category_detail_200(client, category, document):
    url = reverse("documents:category_detail", kwargs={"slug": category.slug})
    response = client.get(url)
    assert response.status_code == 200


@pytest.mark.django_db
def test_category_detail_shows_document(client, category, document):
    url = reverse("documents:category_detail", kwargs={"slug": category.slug})
    response = client.get(url)
    assert document.title.encode() in response.content


@pytest.mark.django_db
def test_category_detail_404(client):
    response = client.get(reverse("documents:category_detail", kwargs={"slug": "nonexistent"}))
    assert response.status_code == 404


@pytest.mark.django_db
def test_legacy_dokumenti_fpu_redirects_to_index(client):
    response = client.get("/dokumenti-fpu/")
    assert response.status_code == 301
    assert response["Location"].endswith("/documents/")


@pytest.mark.django_db
def test_legacy_subpath_redirects_to_category(client, category):
    response = client.get("/dokumenti-fpu/postanovi-radi-fpu/")
    assert response.status_code == 301
    assert response["Location"].endswith("/documents/postanovi-radi-fpu/")


@pytest.mark.django_db
def test_slug_alias_redirects(client, category):
    response = client.get("/documents/materiali-vii-zizdu-fpu/")
    assert response.status_code == 301
    assert "materialy-vii-zyizdu-fpu" in response["Location"]


@pytest.mark.django_db
def test_vii_zjizd_alias_resolves(client):
    DocumentCategory.objects.create(
        title="Матеріали VII З'їзду",
        slug="materialy-vii-zyizdu-fpu",
        order=2,
    )
    response = client.get("/documents/materialy-vii-zyizdu-fpu/")
    assert response.status_code == 200
