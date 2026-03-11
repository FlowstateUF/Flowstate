from celery import shared_task

@shared_task
def ingest_task():
    #TODO: move process_textbook here?
    print("Processing textbook")