from .models import IngestionStatus

def ingestion_status(request):
    try:
        status = IngestionStatus.get()
    except Exception:
        status = None
    return {"ingestion_status": status}