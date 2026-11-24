from django.contrib.auth import get_user_model
from django.db.models import Sum

from .models import (
    FinderNotification,
    QRCode,
    QRScan,
    StickerOrder,
    SupportMessage,
)


def admin_dashboard_stats(request):
    if not request.user.is_staff or request.path.rstrip("/") != "/admin":
        return {}

    User = get_user_model()
    paid_orders = StickerOrder.objects.filter(payment_status="paid")
    return {
        "returnloop_admin_stats": {
            "active_users": User.objects.filter(is_active=True).count(),
            "total_orders": StickerOrder.objects.count(),
            "pending_orders": StickerOrder.objects.filter(
                order_status="pending"
            ).count(),
            "active_qr_codes": QRCode.objects.filter(is_active=True).count(),
            "unread_notifications": FinderNotification.objects.filter(
                is_read=False
            ).count(),
            "total_scans": QRScan.objects.count(),
            "unresolved_support": SupportMessage.objects.filter(
                is_resolved=False
            ).count(),
            "recorded_sales": paid_orders.aggregate(
                total=Sum("amount_due")
            )["total"],
            "paid_orders_without_amount": paid_orders.filter(
                amount_due__isnull=True
            ).count(),
        }
    }
