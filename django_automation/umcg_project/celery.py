import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "umcg_project.settings")

app = Celery("umcg_project")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
