# Flowstate Backend

This is the backend code for Flowstate, utilizing Flask.

## Requirements
 - the first time you are running the backend, cd into the backend directory and run the command 'python -m pip install -r requirements.txt' in your terminal
 - this installs all dependencies specified there
 - add secrets to .env
    - create a file called '.env' in the backend folder
    - generate a personal Navigator API key (Navigator Toolkit online) using gpt-oss-20b model
    - Get the Supabase keys Aaron emailed
    - Define the keys in the .env folder

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

- app/clients.py: this is where clients are initialized
    - supabase, qdrant, navigator(?)

- app/services/init.py: this allows for services to be seen as a package
    - imports service functions for easy external imports

- app/services/textbook_service.py: this is where all textbook-related operations are written
    - textbook parsing, chunking, embeddings, vectors

- app/services/supabase_service.py: this is where all supabase storage and database operations are written
    - user creation, authentication
    - upload textbook to supabase storage and database

- app/services/generation_service.py: this is where all study tools will be created/written
    - Create questions, flashcards, quizes, and more