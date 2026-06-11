"""Custom form widgets for the news editor."""
from __future__ import annotations

from tinymce.widgets import AdminTinyMCE


class BodyEditorWidget(AdminTinyMCE):
    """TinyMCE rich-text widget (Joomla-like toolbar via TINYMCE_DEFAULT_CONFIG)."""


# Backward-compatible alias used in older imports/tests.
QuillBodyWidget = BodyEditorWidget
