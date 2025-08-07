# news/tasks.py
from celery import shared_task
from django.core.management import call_command

@shared_task
def fetch_new_content():
    call_command("fetch_youtube")
    call_command("fetch_liberation_times")
    call_command("fetch_debrief")
