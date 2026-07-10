"""Custom User admin — clean form with Unfold theme."""
from __future__ import annotations

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as _BaseUserAdmin
from django.contrib.auth.models import User
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from unfold.admin import ModelAdmin
from unfold.forms import AdminPasswordChangeForm, UserChangeForm, UserCreationForm


# Знімаємо стандартну реєстрацію Django
admin.site.unregister(User)


@admin.register(User)
class UserAdmin(_BaseUserAdmin, ModelAdmin):
    """Адміни та редактори сайту."""

    form = UserChangeForm
    add_form = UserCreationForm
    change_password_form = AdminPasswordChangeForm

    list_display = (
        "get_avatar", "username", "get_full_name_display",
        "email", "get_role", "is_active", "date_joined",
    )
    list_display_links = ("username", "get_full_name_display")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    list_per_page = 25

    # ── Форма ДОДАВАННЯ ────────────────────────────────────────────────────
    add_fieldsets = (
        ("👤 Новий користувач", {
            "fields": ("username", "first_name", "last_name", "email"),
            "description": "Логін для входу в адмінпанель. Ім'я та прізвище — необов'язкові.",
        }),
        ("🔑 Пароль", {
            "fields": ("password1", "password2"),
            "description": "Мінімум 8 символів. Пароль не повинен бути простим.",
        }),
        ("🔐 Рівень доступу", {
            "fields": ("is_active", "is_staff", "is_superuser"),
            "description": (
                "Активний — може входити. "
                "Адміністратор — доступ до адмінпанелі. "
                "Суперадмін — повний доступ без обмежень."
            ),
        }),
    )

    # ── Форма РЕДАГУВАННЯ ──────────────────────────────────────────────────
    fieldsets = (
        ("👤 Профіль", {
            "fields": ("username", "first_name", "last_name", "email"),
        }),
        ("🔑 Пароль", {
            "fields": ("password",),
            "description": (
                'Паролі зберігаються в зашифрованому вигляді. '
                'Щоб змінити — натисніть посилання «змінити пароль» нижче.'
            ),
        }),
        ("🔐 Рівень доступу", {
            "fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
        }),
        ("📅 Дати", {
            "fields": ("last_login", "date_joined"),
            "classes": ("collapse",),
        }),
    )

    readonly_fields = ("last_login", "date_joined")

    @admin.display(description="")
    def get_avatar(self, obj: User) -> str:
        initials = (
            (obj.first_name[:1] + obj.last_name[:1]).upper()
            if obj.first_name or obj.last_name
            else obj.username[:2].upper()
        )
        return format_html(
            '<span style="display:inline-flex;align-items:center;justify-content:center;'
            'width:32px;height:32px;border-radius:50%;background:#1e40af;'
            'color:#fff;font-size:13px;font-weight:600">{}</span>',
            initials,
        )

    @admin.display(description="Ім'я")
    def get_full_name_display(self, obj: User) -> str:
        return obj.get_full_name() or "—"

    @admin.display(description="Роль")
    def get_role(self, obj: User) -> str:
        if obj.is_superuser:
            return format_html('<span style="color:#b45309;font-weight:600">Суперадмін</span>')
        if obj.is_staff:
            return format_html('<span style="color:#1d4ed8;font-weight:600">Адміністратор</span>')
        return format_html('<span style="color:#6b7280">Читач</span>')
