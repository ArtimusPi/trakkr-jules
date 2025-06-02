import os

DATABASE_CONNECTION_STRING = os.environ.get('SQLALCHEMY_DATABASE_URI')
if not DATABASE_CONNECTION_STRING:
    DATABASE_CONNECTION_STRING = os.environ.get('DATABASE_URL')

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'please-set-a-strong-secret-key-in-render-env'

    if DATABASE_CONNECTION_STRING:
        SQLALCHEMY_DATABASE_URI = DATABASE_CONNECTION_STRING
        if SQLALCHEMY_DATABASE_URI.startswith("postgres://"):
            SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace("postgres://", "postgresql://", 1)
    else:
        project_root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
        SQLALCHEMY_DATABASE_URI = 'sqlite:///' + os.path.join(project_root_dir, 'trakkr.db')
        print("INFO: No DB env var, defaulting to local SQLite: ", SQLALCHEMY_DATABASE_URI, flush=True)

    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # print(f"DEBUG_CONFIG: Final SQLALCHEMY_DATABASE_URI: {SQLALCHEMY_DATABASE_URI}", flush=True) # Optional: uncomment for debug
