from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('trakkr.config.Config')
print(f"!!!!!!!!!! INITIALIZED APP WITH DATABASE URI: {app.config.get('SQLALCHEMY_DATABASE_URI')} !!!!!!!!!!", flush=True)

db = SQLAlchemy(app)

# Import models to ensure they are registered with SQLAlchemy
from trakkr import models

# Import views after app and db are initialized to avoid circular imports
# from trakkr.views import main_views # Example, adjust as you create views

# Register Blueprints
from trakkr.views.chore_views import chore_bp
from trakkr.views.user_views import user_bp
from trakkr.views.dashboard_views import dashboard_bp
from trakkr.views.main_views import main_bp # Import main_bp

app.register_blueprint(chore_bp)
app.register_blueprint(user_bp)
app.register_blueprint(dashboard_bp)
app.register_blueprint(main_bp) # Register main_bp

# You might want to register blueprints here if you use them
# from .controllers.some_controller import some_blueprint
# app.register_blueprint(some_blueprint)

@app.cli.command("init_db")
def init_db_command():
 """Creates the database tables."""
 db.create_all()
 print("Database tables created (or already existed via init_db command).")
