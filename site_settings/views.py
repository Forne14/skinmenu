import csv
import fcntl
from pathlib import Path
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.http import HttpResponseNotAllowed
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme


def _append_newsletter_row(csv_path: Path, row: list[str]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    file_exists = csv_path.exists()

    with open(csv_path, "a", newline="", encoding="utf-8") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        writer = csv.writer(handle)
        if not file_exists or csv_path.stat().st_size == 0:
            writer.writerow(["email", "submitted_at", "source_url"])
        writer.writerow(row)
        fcntl.flock(handle, fcntl.LOCK_UN)


def newsletter_subscribe(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    email = (request.POST.get("email") or "").strip()
    if not email:
        return _newsletter_redirect(request, "error", "Email is required.")

    validator = EmailValidator()
    try:
        validator(email)
    except ValidationError:
        return _newsletter_redirect(request, "error", "Invalid email.")

    source_url = (request.POST.get("source_url") or request.META.get("HTTP_REFERER") or "").strip()
    submitted_at = timezone.now().isoformat()

    csv_path = Path(getattr(settings, "NEWSLETTER_CSV_PATH", settings.MEDIA_ROOT / "newsletter_signups.csv"))
    _append_newsletter_row(csv_path, [email, submitted_at, source_url])

    redirect_target = request.META.get("HTTP_REFERER", "/")
    if not url_has_allowed_host_and_scheme(redirect_target, allowed_hosts={request.get_host()}):
        redirect_target = "/"

    return _newsletter_redirect(request, "success", "Thanks for subscribing.")


def _newsletter_redirect(request, status: str, message: str):
    redirect_target = request.META.get("HTTP_REFERER", "/")
    if not url_has_allowed_host_and_scheme(redirect_target, allowed_hosts={request.get_host()}):
        redirect_target = "/"

    parsed = urlparse(redirect_target)
    query = dict(parse_qsl(parsed.query))
    query["newsletter"] = status
    query["newsletter_message"] = message
    updated = parsed._replace(query=urlencode(query))
    return redirect(urlunparse(updated))
