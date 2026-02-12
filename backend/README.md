# Flowstate Backend

This is the backend code for Flowstate, utilizing Flask.

## Requirements
 - the first time you are running the backend, cd into the backend directory and run the command 'python -m pip install -r requirements.txt' in your terminal
 - this installs all dependencies specified there

## Guide
- run run.py
- then start the React app in the frontend

## Files
- run.py: only file that needs to be run, creates an app using init.py
    - this file never really needs to be modified

- app/init.py: this creates the flask app, and uses the db and routes
    - various config and extensions could be added here down the line

- app/db.py: this is where the database is initialized, and all models are created and defined
    - this is where tables and there schema are created

- app/routes.py: this is where HTTP routes can be written, rather than writing them all in init.py
    - this is where additional website routes will be added to handle various requests

- app/supabase_client.py: this is where the supabase storage client is initialized
    - uses credentials from .env

- services/init.py: this allows for services to be seen as a package
    - imports service functions for easy external imports

- services/db_service.py: this is where all database-related operations are written

- services/parsing_service.py: this is where all document parsing operations are written

- services/storage_service.py: this is where all supabase storage operations are written

- services/study_servicel.py: this is where all study tools will be created/written
    - Create questions, flashcards, quizes, and more