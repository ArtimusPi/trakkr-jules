import pytest
from trakkr import app as main_app
from trakkr import db as main_db
from run import create_sample_data, create_tables_if_needed # Import your setup functions

@pytest.fixture(scope='session')
def app():
    """Session-wide test Flask application."""
    main_app.config.update({
        "TESTING": True,
        "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",  # Use in-memory SQLite for tests
        "WTF_CSRF_ENABLED": False, # Disable CSRF for forms if you have them and test them
        "DEBUG": False,
        "SECRET_KEY": "test_secret_key" # Consistent secret key for tests
    })
    return main_app

@pytest.fixture(scope='session')
def db(app):
    """Session-wide database for testing."""
    with app.app_context():
        # create_tables_if_needed() will check if tables exist (based on URI)
        # For :memory:, it will always create.
        # We need to ensure create_all is called for the in-memory DB.
        main_db.create_all() 
        
        # Populate with sample data
        # Note: create_sample_data might print to console, which is fine for tests.
        # It also now attempts to create users with specific IDs 1, 2, 3.
        print("Creating sample data for test database...")
        create_sample_data()
        print("Sample data creation complete for test database.")

        yield main_db  # Provide the database session for tests to use

        main_db.session.remove()
        main_db.drop_all()

@pytest.fixture(scope='function') # Function scope for client to ensure clean state for each test
def client(app, db_session): # db_session ensures DB is ready
    """A test client for the app."""
    return app.test_client()

@pytest.fixture(scope='function')
def db_session(db):
    """
    Provides a transactional scope around a test function.
    Ensures that the database is clean after each test, if tests modify data
    and don't clean up themselves. For tests that rely on initial sample data
    and don't modify it extensively, this might be more than needed, but
    it's good practice for tests that do create/modify/delete.
    
    However, our create_sample_data runs once per session. If tests modify this
    shared data, they might interfere. For more robust tests, each test
    might need to reset and recreate sample data, or tests must be written
    to be independent of modifications by other tests.

    For now, let's assume tests will mostly read sample data or add new, non-conflicting data.
    If tests heavily modify the sample data (e.g. delete user 1), subsequent tests might fail.
    A more robust approach might involve:
    1. `db` fixture creates schema.
    2. A separate fixture, perhaps function-scoped, that populates data before each test.
    
    Let's keep it simple: `db` fixture (session-scoped) creates schema and sample data once.
    `db_session` here will just yield the main_db.session for convenience in tests.
    Tests should be careful about modifying shared sample data.
    """
    yield db.session # Provide the SQLAlchemy session
    # db.session.rollback() # Optional: if tests commit, rollback to keep sample data pristine for next test
    # For now, we assume tests don't destructively modify the initial sample data in a way that breaks other tests.
    # If they do, a more complex per-test data setup/teardown will be needed.
