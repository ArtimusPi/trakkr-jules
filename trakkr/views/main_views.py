from flask import Blueprint, render_template

main_bp = Blueprint('main_bp', __name__)

@main_bp.route('/')
def index():
    # In a real app, you'd have login logic.
    # Here, we just provide links to dashboards assuming fixed IDs for sample users.
    # Sample users (IDs assumed: parent1=1, kid1=2, kid2=3)
    # These IDs should match those expected or created in `run.py` `create_sample_data`
    sample_users = [
        {'id': 1, 'username': 'parent1', 'role': 'parent', 'link': '/dashboards/parent/1'},
        {'id': 2, 'username': 'kid1', 'role': 'kid', 'link': '/dashboards/kid/2'},
        {'id': 3, 'username': 'kid2', 'role': 'kid', 'link': '/dashboards/kid/3'}
    ]
    return render_template('index.html', sample_users=sample_users)
