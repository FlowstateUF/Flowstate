# Flowstate Backend

This is the backend code for Flowstate, utilizing Flask.

## Requirements
 - the first time you are running the backend, cd into the backend directory and run the command 'python -m pip install -r requirements.txt' in your terminal
 - this installs all dependencies specified there

## Guide
- run run.py
- then start the React app in the frontend

## Files
- db.py: this is where the database is initialized, and all models are created and defined
    - this is where tables and there schema are created

- init.py: this creates the flask app, and uses the db and routes
    - various config and extensions could be added here down the line

- routes.py: this is where HTTP routes can be written, rather than writing them all in init.py
    - this is where additioanl website routes will be added to handle various requests

- run.py: only file that needs to be run, creates an app using init.py
    - this file never really needs to be modified