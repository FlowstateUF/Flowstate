from celery import shared_task

@shared_task
def process_textbook():
    print("Processing textbook")