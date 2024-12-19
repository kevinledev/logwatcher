from django.db import models
import uuid


class Event(models.Model):
    HTTP_METHODS = ["GET", "POST", "PUT", "DELETE"]

    method = models.CharField(
        max_length=10,
        choices=[(m, m) for m in HTTP_METHODS],
        help_text="HTTP method used for the request",
    )

    source = models.CharField(
        max_length=100,
    )
    timestamp = models.DateTimeField(auto_now_add=True)
    duration_ms = models.IntegerField()
    status_code = models.IntegerField()
    request_id = models.UUIDField(
        default=uuid.uuid4, unique=True, help_text="Unique identifier for the request"
    )
    metadata = models.JSONField(default=dict)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["-timestamp"]),
            models.Index(fields=["status_code"]),
            models.Index(fields=["method"]),
        ]

        def __str__(self):
            return f"{self.method} {self.source} - {self.status_code} ({self.duration_ms}ms)"
