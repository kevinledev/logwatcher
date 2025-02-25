# Generated by Django 5.1.4 on 2024-12-18 20:17

import uuid
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "method",
                    models.CharField(
                        choices=[
                            ("GET", "GET"),
                            ("POST", "POST"),
                            ("PUT", "PUT"),
                            ("DELETE", "DELETE"),
                        ],
                        help_text="HTTP method used for the request",
                        max_length=10,
                    ),
                ),
                ("source", models.CharField(max_length=100)),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("duration_ms", models.IntegerField()),
                ("status_code", models.IntegerField()),
                (
                    "request_id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        help_text="Unique identifier for the request",
                        unique=True,
                    ),
                ),
                ("metadata", models.JSONField(default=dict)),
            ],
            options={
                "ordering": ["-timestamp"],
                "indexes": [
                    models.Index(
                        fields=["-timestamp"], name="events_even_timesta_5c8baa_idx"
                    ),
                    models.Index(
                        fields=["status_code"], name="events_even_status__6b20bc_idx"
                    ),
                    models.Index(
                        fields=["method"], name="events_even_method_23204c_idx"
                    ),
                ],
            },
        ),
    ]
