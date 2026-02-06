from app import create_app

# ** Entry point to run the backend **

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5001)