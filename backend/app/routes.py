from flask import jsonify

# ** Where HTTP routes are written **

# register_routes is called in init.py, giving it access to all the routes below 
def register_routes(app):
    
    @app.get("/")
    def root():
        return jsonify({"message": "Flowstate backend running"})


