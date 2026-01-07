from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, Http404
from wagtail.documents import get_document_model

@staff_member_required
def document_url(request, doc_id: int):
    Document = get_document_model()
    try:
        doc = Document.objects.get(pk=doc_id)
    except Document.DoesNotExist:
        raise Http404

    # This respects WAGTAILDOCS_SERVE_METHOD (direct/redirect/serve_view) via doc.url
    return JsonResponse({"url": doc.url})
