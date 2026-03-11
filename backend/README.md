# Flowstate Backend

This is the backend code for Flowstate, utilizing Flask.

## Requirements
 - the first time you are running the backend, cd into the backend directory and run the command 'python -m pip install -r requirements.txt' in your terminal
 - this installs all dependencies specified there
 - add secrets to .env
    - create a file called '.env' in the backend folder
    - generate a personal Navigator API key (Navigator Toolkit online) using gpt-oss-20b model
    - Get other keys from email
    - check .env.example

## Guide
- run run.py
- then start the React app in the frontend

## Files

### backend/
- run.py: only file that needs to be run, creates an app using init.py
    - this file never really needs to be modified

- make_celery.py: celery worker

### backend/app/

- __init__.py: this creates the flask app, and uses the db and routes
    - various config and extensions could be added here down the line

- celery_app.py: this create the celery app

- celery_tasks.py: this is where the celery tasks will be maybe

- clients.py: this is where clients are initialized
    - supabase, qdrant

- config.py: this is where our Setting class is defined
    - allows us to use secrets

- processing.py: this is where the textbook processing pipeline is

- routes.py: this is where HTTP routes can be written, rather than writing them all in init.py
    - this is where additional website routes will be added to handle various requests

### backend/app/services/

- embedding_service.py: creates embeddings using sentence_transformers library
    - uses all-MiniLM-L6-v2 model

- llm_service.py: this is where all llm generation operations are

- question_prompts.py: this file is where system prompts are stored

- supabase_service.py: this is where all supabase storage and database operations are
    - user creation, authentication
    - upload textbook to supabase storage and database

- textbook_service.py: this is where all textbook-related operations are
    - textbook parsing, chunking, embeddings, vectors

- vector_service.py: this is where all vector/qdrant-related operations are

## Notes
- Can think about using Supabase Auth
- Can improve image embeddings

## Processing Workflow
    User uploads PDF
        ↓
    Flask returns 202 immediately  ← user can navigate freely
        ↓
    Redis queue
        ↓
    ingest_task (worker 1)
        → parses all pages
        → embeds + upserts
        → marks textbook "ready"  ← textbook searchable from here
        → pretest_task.delay()    ← fires and forgets
        ↓
    pretest_task (worker 2, runs in parallel)
        → generate_all_pretests
        → stores in Supabase

