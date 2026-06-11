"""Tests for JoomGallery local path helpers."""
from pathlib import Path

import pytest
from django.conf import settings

from apps.gallery.utils import local_file_exists, photo_local_path, resolved_media_url


def test_photo_local_path_with_catpath():
    path = photo_local_path("_1_20131202_1677194344.jpg", "_______29__2013____81")
    assert path == (
        "images/joomgallery/originals/_______29__2013____81/_1_20131202_1677194344.jpg"
    )


def test_photo_local_path_without_catpath():
    assert photo_local_path("foo.jpg", "") == "images/stories/foo.jpg"


@pytest.mark.django_db
def test_resolved_media_url_missing_file():
    assert resolved_media_url("images/stories/does-not-exist.jpg") == ""


@pytest.mark.django_db
def test_resolved_media_url_existing_file(tmp_path, settings):
    settings.MEDIA_ROOT = tmp_path
    rel = "joomla_images/images/test/sample.jpg"
    target = tmp_path / rel
    target.parent.mkdir(parents=True)
    target.write_bytes(b"fake")
    assert resolved_media_url("images/test/sample.jpg") == "/media/joomla_images/images/test/sample.jpg"
    assert local_file_exists("images/test/sample.jpg")
