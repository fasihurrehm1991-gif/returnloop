from django.contrib import admin, messages
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from django.conf import settings
from django.http import HttpResponse
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html

from io import BytesIO
from pathlib import Path

import qrcode
import uuid

from PIL import Image, ImageDraw, ImageFont

from .models import (
    UserProfile,
    QRCode,
    StickerOrder,
    FinderNotification,
    QRScan,
    SupportMessage
)


User = get_user_model()


# =====================================================
# CREATE COMPACT RETURNLOOP QR STICKER
# =====================================================

def create_sticker(qr_matrix):

    width = 440
    height = 440
    qr_size = 340

    black = (15, 20, 18)
    green = (0, 170, 100)
    white = (255, 255, 255)

    sticker = Image.new("RGB", (width, height), white)
    draw = ImageDraw.Draw(sticker)

    draw.rounded_rectangle(
        (5, 5, 435, 435),
        radius=24,
        fill=white,
        outline=green,
        width=3
    )

    matrix_size = len(qr_matrix)
    module_size = qr_size / matrix_size

    qr_x = (width - qr_size) // 2
    qr_y = 15

    finder_positions = [
        (4, 4),
        (matrix_size - 11, 4),
        (4, matrix_size - 11)
    ]

    for row in range(matrix_size):

        for col in range(matrix_size):

            if not qr_matrix[row][col]:
                continue

            inside_finder = any(
                fx <= col < fx + 7 and
                fy <= row < fy + 7
                for fx, fy in finder_positions
            )

            if inside_finder:
                continue

            x0 = qr_x + col * module_size
            y0 = qr_y + row * module_size

            dot_size = module_size * 0.72
            gap = (module_size - dot_size) / 2

            draw.ellipse(
                (
                    x0 + gap,
                    y0 + gap,
                    x0 + gap + dot_size,
                    y0 + gap + dot_size
                ),
                fill=black
            )

    for fx, fy in finder_positions:

        x0 = qr_x + fx * module_size
        y0 = qr_y + fy * module_size

        x1 = x0 + 7 * module_size
        y1 = y0 + 7 * module_size

        draw.rectangle(
            (x0, y0, x1, y1),
            fill=black
        )

        draw.rectangle(
            (
                x0 + module_size,
                y0 + module_size,
                x1 - module_size,
                y1 - module_size
            ),
            fill=white
        )

        draw.rectangle(
            (
                x0 + 2 * module_size,
                y0 + 2 * module_size,
                x1 - 2 * module_size,
                y1 - 2 * module_size
            ),
            fill=black
        )

    logo_path = (
        Path(settings.BASE_DIR)
        / "static"
        / "images"
        / "returnloop-logo.png.png"
    )

    if not logo_path.exists():

        raise FileNotFoundError(
            "ReturnLoop logo was not found in static/images."
        )

    logo = Image.open(logo_path).convert("RGBA")

    pixels = logo.load()

    for y in range(logo.height):

        for x in range(logo.width):

            r, g, b, a = pixels[x, y]

            if r > 240 and g > 240 and b > 240:
                pixels[x, y] = (r, g, b, 0)

    bbox = logo.getbbox()

    if bbox:
        logo = logo.crop(bbox)

    logo.thumbnail(
        (76, 76),
        Image.Resampling.LANCZOS
    )

    center_x = width // 2
    center_y = qr_y + qr_size // 2

    draw.ellipse(
        (
            center_x - 47,
            center_y - 47,
            center_x + 47,
            center_y + 47
        ),
        fill=white,
        outline=green,
        width=3
    )

    logo_x = center_x - logo.width // 2
    logo_y = center_y - logo.height // 2

    sticker.paste(
        logo,
        (logo_x, logo_y),
        logo
    )

    try:

        font = ImageFont.truetype(
            "C:/Windows/Fonts/arialbd.ttf",
            17
        )

    except OSError:

        font = ImageFont.load_default()

    first_text = "IF FOUND,"
    second_text = "SCAN TO NOTIFY THE OWNER."

    first_width = draw.textbbox(
        (0, 0),
        first_text,
        font=font
    )[2]

    second_width = draw.textbbox(
        (0, 0),
        second_text,
        font=font
    )[2]

    spacing = 6

    total_width = first_width + spacing + second_width

    start_x = (width - total_width) // 2

    draw.text(
        (start_x, 370),
        first_text,
        fill=green,
        font=font
    )

    draw.text(
        (start_x + first_width + spacing, 370),
        second_text,
        fill=black,
        font=font
    )

    return sticker


# =====================================================
# QR CODE ADMIN ACTIONS
# =====================================================

@admin.action(description="Activate Selected QR Codes")
def activate_qr_codes(modeladmin, request, queryset):

    if not request.user.is_superuser:

        modeladmin.message_user(
            request,
            "Only the main administrator can perform this action.",
            level=messages.ERROR
        )

        return

    updated = 0
    skipped = 0

    for qr_code in queryset.select_related("user"):
        has_delivered_paid_order = StickerOrder.objects.filter(
            user=qr_code.user,
            payment_status="paid",
            order_status__in=("delivered", "active")
        ).exists()

        if not has_delivered_paid_order:
            skipped += 1
            continue

        qr_code.is_active = True
        qr_code.save(update_fields=["is_active"])
        StickerOrder.objects.filter(
            user=qr_code.user,
            payment_status="paid",
            order_status="delivered"
        ).update(order_status="active")
        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} QR code(s) activated. "
        f"{skipped} skipped because no paid, delivered order was found."
    )


@admin.action(description="Deactivate Selected QR Codes")
def deactivate_qr_codes(modeladmin, request, queryset):

    if not request.user.is_superuser:

        modeladmin.message_user(
            request,
            "Only the main administrator can perform this action.",
            level=messages.ERROR
        )

        return

    updated = 0

    for qr_code in queryset.select_related("user"):
        qr_code.is_active = False
        qr_code.save(update_fields=["is_active"])
        StickerOrder.objects.filter(
            user=qr_code.user,
            order_status="active"
        ).update(order_status="delivered")
        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} QR code(s) deactivated successfully."
    )


@admin.action(description="Replace Selected QR Codes")
def replace_qr_codes(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Only the main administrator can replace QR codes.",
            level=messages.ERROR
        )
        return

    replaced = 0
    for qr_code in queryset.select_related("user"):
        qr_code.token = uuid.uuid4()
        qr_code.is_active = False
        qr_code.replaced_at = timezone.now()
        qr_code.save(update_fields=["token", "is_active", "replaced_at"])
        StickerOrder.objects.filter(
            user=qr_code.user,
            order_status="active"
        ).update(order_status="delivered")
        replaced += 1

    modeladmin.message_user(
        request,
        f"{replaced} QR code(s) replaced and deactivated. "
        "Activate the replacement after its order is ready."
    )


@admin.action(description="Download Branded QR Sticker")
def download_qr_code(modeladmin, request, queryset):

    if not request.user.is_superuser:

        modeladmin.message_user(
            request,
            "Only the main administrator can download QR stickers.",
            level=messages.ERROR
        )

        return

    if queryset.count() != 1:

        modeladmin.message_user(
            request,
            "Please select exactly one QR code.",
            level=messages.ERROR
        )

        return

    qr_code = queryset.first()

    scan_url = request.build_absolute_uri(
        reverse("scan_qr", args=[qr_code.token])
    )

    qr = qrcode.QRCode(
        version=None,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=12,
        border=4
    )

    qr.add_data(scan_url)
    qr.make(fit=True)

    qr_matrix = qr.get_matrix()

    try:

        sticker = create_sticker(qr_matrix)

    except FileNotFoundError as error:

        modeladmin.message_user(
            request,
            str(error),
            level=messages.ERROR
        )

        return

    buffer = BytesIO()

    sticker.save(
        buffer,
        format="PNG",
        dpi=(300, 300)
    )

    response = HttpResponse(
        buffer.getvalue(),
        content_type="image/png"
    )

    response["Content-Disposition"] = (
        f'attachment; filename="ReturnLoop_Sticker_{qr_code.user.username}.png"'
    )

    return response


# =====================================================
# ORDER ADMIN ACTIONS
# =====================================================

@admin.action(description="Mark Selected Orders as Delivered")
def mark_orders_delivered(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for order in queryset:
        if (
            order.payment_status != "paid"
            or not QRCode.objects.filter(user=order.user).exists()
            or order.order_status not in ("paid", "shipped", "delivered")
        ):
            skipped += 1
            continue
        order.order_status = "delivered"
        order.save(update_fields=["order_status"])
        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} order(s) marked as delivered. "
        f"{skipped} skipped: payment or QR requirements missing."
    )


@admin.action(description="Mark Selected Payments as Paid")
def mark_payments_paid(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for order in queryset.select_related("user"):
        if (
            order.amount_due is None
            or order.order_status == "cancelled"
        ):
            skipped += 1
            continue
        if not QRCode.objects.filter(user=order.user).exists():
            skipped += 1
            continue

        order.payment_status = "paid"
        if order.order_status in ("pending", "generated", "processing"):
            order.order_status = "paid"
        order.save(update_fields=["payment_status", "order_status"])
        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} payment(s) marked as paid. "
        f"{skipped} skipped: issue a QR and enter the agreed price first."
    )


@admin.action(description="Mark Selected Payments as Unpaid")
def mark_payments_unpaid(modeladmin, request, queryset):
    updated = 0
    skipped = 0
    for order in queryset:
        if order.order_status in ("delivered", "active"):
            skipped += 1
            continue
        order.payment_status = "unpaid"
        if order.order_status == "paid":
            order.order_status = (
                "generated"
                if QRCode.objects.filter(user=order.user).exists()
                else "pending"
            )
        order.save(update_fields=["payment_status", "order_status"])
        updated += 1

    modeladmin.message_user(
        request,
        f"{updated} payment(s) marked as unpaid. "
        f"{skipped} delivered or active order(s) were left unchanged."
    )


@admin.action(description="Issue QR and Mark Orders Generated")
def generate_order_qr_codes(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Only the main administrator can issue QR codes.",
            level=messages.ERROR
        )
        return

    generated = 0
    skipped = 0
    for order in queryset.select_related("user"):
        if order.order_status not in ("pending", "processing", "generated"):
            skipped += 1
            continue
        QRCode.objects.get_or_create(user=order.user)
        order.order_status = "generated"
        order.save(update_fields=["order_status"])
        generated += 1

    modeladmin.message_user(
        request,
        f"QR issued for {generated} order(s). "
        f"{skipped} cancelled order(s) skipped."
    )


@admin.action(description="Mark Delivered Orders Active")
def activate_delivered_orders(modeladmin, request, queryset):
    if not request.user.is_superuser:
        modeladmin.message_user(
            request,
            "Only the main administrator can activate QR codes.",
            level=messages.ERROR
        )
        return

    activated = 0
    skipped = 0
    for order in queryset.select_related("user"):
        qr_code = QRCode.objects.filter(user=order.user).first()
        if (
            order.payment_status != "paid"
            or order.order_status != "delivered"
            or qr_code is None
        ):
            skipped += 1
            continue

        qr_code.is_active = True
        qr_code.save(update_fields=["is_active"])
        order.order_status = "active"
        order.save(update_fields=["order_status"])
        activated += 1

    modeladmin.message_user(
        request,
        f"{activated} delivered order(s) activated. "
        f"{skipped} skipped: payment, delivery, or QR requirements missing."
    )


# =====================================================
# USER MANAGEMENT ADMIN
# =====================================================

class ReturnLoopUserAdmin(UserAdmin):

    list_display = (
        "username",
        "email",
        "first_name",
        "last_name",
        "display_member_type",
        "is_active",
        "is_staff",
        "date_joined"
    )

    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
        "date_joined"
    )

    search_fields = (
        "username",
        "email",
        "first_name",
        "last_name"
    )

    ordering = (
        "-date_joined",
    )

    list_per_page = 25

    @admin.display(description="Member Type")
    def display_member_type(self, obj):
        profile = getattr(obj, "userprofile", None)
        if profile and profile.member_type:
            return profile.get_member_type_display()
        return "-"


# Replace Django's default User admin with ReturnLoop's improved version.

if admin.site.is_registered(User):
    admin.site.unregister(User)

admin.site.register(User, ReturnLoopUserAdmin)


# =====================================================
# QR CODE ADMIN
# =====================================================

@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):

    list_display = (
        "display_owner",
        "display_email",
        "display_token",
        "display_status",
        "generated_at",
        "replaced_at"
    )

    list_filter = (
        "is_active",
        "generated_at",
        "replaced_at"
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email",
        "token"
    )

    readonly_fields = (
        "token",
        "display_scan_url",
        "generated_at",
        "replaced_at"
    )

    fields = (
        "user",
        "token",
        "display_scan_url",
        "is_active",
        "generated_at",
        "replaced_at"
    )

    actions = [
        activate_qr_codes,
        deactivate_qr_codes,
        download_qr_code,
        replace_qr_codes
    ]

    @admin.display(description="QR Owner", ordering="user__username")
    def display_owner(self, obj):

        name = (
            obj.user.get_full_name()
            or obj.user.username
        )

        return name

    @admin.display(description="Email", ordering="user__email")
    def display_email(self, obj):

        return obj.user.email or "-"

    @admin.display(description="QR Token")
    def display_token(self, obj):

        return str(obj.token)

    @admin.display(description="QR Status", ordering="is_active")
    def display_status(self, obj):

        if obj.is_active:

            return format_html(
                '<strong style="color:green;">● Active</strong>'
            )

        return format_html(
            '<strong style="color:red;">● Inactive</strong>'
        )

    @admin.display(description="QR Scanning URL")
    def display_scan_url(self, obj):

        relative_url = reverse(
            "scan_qr",
            args=[obj.token]
        )

        return format_html(
            '<input type="text" value="{}" readonly '
            'style="width:100%;max-width:500px;padding:8px;" '
            'onclick="this.select();">',
            relative_url
        )

    def has_module_permission(self, request):
        return request.user.is_superuser

    def has_view_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_change_permission(self, request, obj=None):
        return request.user.is_superuser

    def has_add_permission(self, request):
        return request.user.is_superuser

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser


# =====================================================
# STICKER ORDER ADMIN
# =====================================================

@admin.register(StickerOrder)
class StickerOrderAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "display_customer",
        "package",
        "quantity",
        "amount_due",
        "order_status",
        "payment_status",
        "created_at"
    )

    list_filter = (
        "order_status",
        "payment_status",
        "package",
        "created_at"
    )

    search_fields = (
        "user__username",
        "user__first_name",
        "user__last_name",
        "user__email"
    )

    readonly_fields = (
        "created_at",
    )

    ordering = (
        "-created_at",
    )

    date_hierarchy = "created_at"

    list_per_page = 25

    actions = [
        generate_order_qr_codes,
        mark_orders_delivered,
        mark_payments_paid,
        mark_payments_unpaid,
        activate_delivered_orders
    ]

    fieldsets = (
        ("Customer Information", {
            "fields": (
                "user",
            )
        }),

        ("Order Details", {
            "fields": (
                "package",
                "quantity",
                "amount_due",
            )
        }),

        ("Order Processing", {
            "fields": (
                "order_status",
                "payment_status",
                "created_at",
            )
        }),
    )

    @admin.display(description="Customer", ordering="user__username")
    def display_customer(self, obj):

        name = (
            obj.user.get_full_name()
            or obj.user.username
        )

        return format_html(
            '<strong>{}</strong><br>'
            '<small style="color:#718096;">{}</small>',
            name,
            obj.user.email or "No email"
        )


# =====================================================
# USER PROFILE ADMIN
# =====================================================

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):

    list_display = (
        "full_name",
        "user",
        "phone",
        "member_type",
        "institution_name",
        "affiliation_id",
        "created_at"
    )

    search_fields = (
        "full_name",
        "phone",
        "institution_name",
        "affiliation_id",
        "user__username",
        "user__email"
    )

    readonly_fields = (
        "created_at",
    )


# =====================================================
# FINDER NOTIFICATION ADMIN
# =====================================================

@admin.register(FinderNotification)
class FinderNotificationAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "display_owner",
        "location",
        "is_read",
        "created_at"
    )

    list_filter = (
        "is_read",
        "created_at"
    )

    search_fields = (
        "qr_code__user__username",
        "message",
        "location"
    )

    readonly_fields = (
        "created_at",
    )

    @admin.display(description="QR Owner")
    def display_owner(self, obj):

        return obj.qr_code.user.username


# =====================================================
# QR SCAN ADMIN
# =====================================================

@admin.register(QRScan)
class QRScanAdmin(admin.ModelAdmin):

    list_display = (
        "id",
        "display_owner",
        "scanned_at"
    )

    list_filter = (
        "scanned_at",
    )

    search_fields = (
        "qr_code__user__username",
    )

    readonly_fields = (
        "scanned_at",
    )

    @admin.display(description="QR Owner")
    def display_owner(self, obj):

        return obj.qr_code.user.username


@admin.register(SupportMessage)
class SupportMessageAdmin(admin.ModelAdmin):
    list_display = (
        "subject",
        "name",
        "email",
        "is_resolved",
        "submitted_at",
    )
    list_filter = ("is_resolved", "submitted_at")
    list_editable = ("is_resolved",)
    search_fields = ("name", "email", "subject", "message")
    readonly_fields = ("submitted_at",)
    ordering = ("is_resolved", "-submitted_at")
    date_hierarchy = "submitted_at"
    list_per_page = 25

    def has_add_permission(self, request):
        return False