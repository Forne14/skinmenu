# /media_derivatives/views.py
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from django.contrib.admin.views.decorators import staff_member_required

from .models import VideoDerivative


@require_GET
@staff_member_required
def derivatives_status(request, document_id: int):
    qs = VideoDerivative.objects.filter(document_id=document_id).select_related("poster_image")

    payload = []
    for d in qs:
        payload.append(
            {
                "kind": d.kind,
                "status": d.status,
                "progress": d.progress,
                "error": d.error,
                "rq_job_id": d.rq_job_id,
                "file_url": d.file.url if d.file else "",
                "poster_url": (d.poster_image.file.url if d.poster_image else ""),
                "updated_at": d.updated_at.isoformat(),
            }
        )

    return JsonResponse({"document_id": document_id, "derivatives": payload})
