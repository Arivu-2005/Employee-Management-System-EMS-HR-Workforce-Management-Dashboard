import os
from flask import Flask, send_from_directory, jsonify
from flask_cors import CORS
from config import Config
from database import get_db

# Import blueprints
from routes.auth import auth_bp
from routes.employees import employees_bp
from routes.departments import departments_bp
from routes.attendance import attendance_bp
from routes.leaves import leaves_bp
from routes.payroll import payroll_bp
from routes.performance import performance_bp
from routes.dashboard import dashboard_bp
from routes.reports import reports_bp
from routes.settings import settings_bp

def create_app():
    # Frontend directory path
    frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'frontend'))

    app = Flask(__name__, static_folder=frontend_dir, static_url_path='')
    app.config.from_object(Config)

    # Enable CORS
    CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

    # Ensure database is connected and seeded
    with app.app_context():
        try:
            get_db()
        except Exception as e:
            print(f"[App Init] Database connection notice: {e}")

    # Register API blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(departments_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(leaves_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(reports_bp)
    app.register_blueprint(settings_bp)

    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            "status": "healthy",
            "service": "Employee Management System API",
            "version": "2.0.0"
        }), 200

    @app.route('/uploads/<filename>', methods=['GET'])
    def serve_uploaded_file(filename):
        return send_from_directory(Config.UPLOAD_FOLDER, filename)

    # Serve Frontend Pages & Assets
    @app.route('/', methods=['GET'])
    def index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/<path:path>', methods=['GET'])
    def serve_frontend(path):
        target = os.path.join(frontend_dir, path)
        if os.path.exists(target):
            return send_from_directory(frontend_dir, path)
        # If file ends with .html, or fallback
        if not path.startswith('api/'):
            html_candidate = target + '.html'
            if os.path.exists(html_candidate):
                return send_from_directory(frontend_dir, path + '.html')
            return send_from_directory(frontend_dir, 'index.html')
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "message": "Resource not found"}), 404

    @app.errorhandler(500)
    def internal_error(e):
        return jsonify({"success": False, "message": "Internal server error"}), 500

    return app

app = create_app()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting Employee Management System server on http://localhost:{port}")
    app.run(host='0.0.0.0', port=port, debug=Config.DEBUG)
