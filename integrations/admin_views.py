from django.core.paginator import Paginator
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required

from integrations.models import OutboundEvent


@staff_member_required
def outbound_events_view(request):
    status = (request.GET.get("status") or "").strip()
    qs = OutboundEvent.objects.all().order_by("-created_at")
    if status:
        qs = qs.filter(status=status)
    paginator = Paginator(qs, 50)
    page = paginator.get_page(request.GET.get("page"))
    return render(
        request,
        "wagtailadmin/integrations/outbound_events.html",
        {
            "events_page": page,
            "status": status,
            "status_choices": OutboundEvent.STATUS_CHOICES,
        },
    )

