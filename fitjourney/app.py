from . import create_app

# Create the app instance using the factory
app = create_app()

if __name__ == '__main__':
    # You can configure host and port here if needed
    # Example: app.run(debug=True, host='0.0.0.0', port=5000)
    app.run(debug=True)