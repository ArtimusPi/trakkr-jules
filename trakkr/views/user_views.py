from flask import Blueprint, jsonify
from trakkr import db
from trakkr.models import User, ChoreAssignment, Chore

user_bp = Blueprint('user_bp', __name__, url_prefix='/users')

@user_bp.route('/<int:user_id>/chores', methods=['GET'])
def get_assigned_chores(user_id):
    user = User.query.get(user_id)
    if not user:
        return jsonify({'error': 'User not found'}), 404

    if user.role != 'kid':
        return jsonify({'error': 'User is not a kid, cannot have assigned chores in this context'}), 400

    # Fetch assignments that are not yet completed
    assignments = ChoreAssignment.query.filter_by(user_id=user_id).filter(ChoreAssignment.status != 'completed').all()
    
    # # Alternative: Fetch all assignments and let client filter (if 'overdue' or other statuses are complex)
    # assignments = ChoreAssignment.query.filter_by(user_id=user_id).all()


    output_chores = []
    for assignment in assignments:
        chore = Chore.query.get(assignment.chore_id) # Get chore details
        if chore:
            output_chores.append({
                'assignment_id': assignment.id,
                'chore_id': chore.id,
                'chore_name': chore.name,
                'chore_description': chore.description,
                'assigned_at': assignment.assigned_at.isoformat(),
                'status': assignment.status
            })

    return jsonify({'assigned_chores': output_chores}), 200
