# automation/tasks.py
from celery import shared_task
from playwright_scripts.login_script import vodafone_login
from django.core.cache import cache

def _store_stream_to_cache(token, generator):
    for message in generator:
        cache.set(f"celery_stream:{token}", message, timeout=300)

def _vodafone_login_wrapper(username, password, token):
    return _store_stream_to_cache(token, vodafone_login(username, password, token))

@shared_task(bind=True)
def start_vodafone_login_task(self, username, password, token):
    try:
        _vodafone_login_wrapper(username, password, token)
    except Exception as e:
        cache.set(f"celery_stream:{token}", f'data: {{"message": "❌ Fout in Celery: {str(e)}", "success": false}}\n\n', timeout=300)
