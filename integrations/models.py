from django.db import models
from django.utils import timezone


class OutboundEvent(models.Model):
    STATUS_PENDING = "pending"
    STATUS_SENT = "sent"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_SENT, "Sent"),
        (STATUS_FAILED, "Failed"),
    ]

    EVENT_NEWSLETTER_SIGNUP = "newsletter_signup"

    event_type = models.CharField(max_length=64, db_index=True)
    destination = models.CharField(max_length=64, default="webhook")
    payload = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_PENDING, db_index=True)
    attempts = models.PositiveIntegerField(default=0)
    last_error = models.TextField(blank=True)
    sent_at = models.DateTimeField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def mark_sent(self) -> None:
        self.status = self.STATUS_SENT
        self.sent_at = timezone.now()
        self.last_error = ""
        self.attempts = self.attempts + 1
        self.save(update_fields=["status", "sent_at", "last_error", "attempts", "updated_at"])

    def mark_failed(self, error: str) -> None:
        self.status = self.STATUS_FAILED
        self.last_error = (error or "").strip()[:1000]
        self.attempts = self.attempts + 1
        self.save(update_fields=["status", "last_error", "attempts", "updated_at"])
