from flask import Blueprint, jsonify, render_template, current_app, flash, redirect, url_for
from trakkr import db
from trakkr.models import User, Chore, ChoreAssignment
from sqlalchemy.orm import joinedload
import requests # For internal API calls if that pattern is chosen, or call functions directly

dashboard_bp = Blueprint('dashboard_bp', __name__, url_prefix='/dashboards')

# ---- API Endpoints (JSON) ----
@dashboard_bp.route('/api/parent/<int:parent_id>', methods=['GET'])
def get_parent_dashboard_api(parent_id):
    parent = User.query.get(parent_id)
    if not parent:
        return jsonify({'error': 'Parent user not found'}), 404
    if parent.role != 'parent':
        return jsonify({'error': 'User is not a parent'}), 403

    # Chores created by this parent
    chores_created = Chore.query.filter_by(created_by_id=parent.id).all()
    
    response_chores = []
    for chore in chores_created:
        assignments_data = []
        # Get current assignments for each chore
        current_assignments = ChoreAssignment.query.filter_by(chore_id=chore.id).all()
        for assign in current_assignments:
            kid_user = User.query.get(assign.user_id)
            assignments_data.append({
                'assignment_id': assign.id,
                'kid_id': assign.user_id,
                'kid_username': kid_user.username if kid_user else 'Unknown Kid',
                'assigned_at': assign.assigned_at.isoformat(),
                'status': assign.status,
                'completed_at': assign.completed_at.isoformat() if assign.completed_at else None
            })
        
        response_chores.append({
            'chore_id': chore.id,
            'name': chore.name,
            'description': chore.description,
            'assignments': assignments_data
        })

    # For now, we don't have a direct link from parent to kids other than through chore creation/assignment.
    # So, we list all kids who have chores assigned that were created by this parent.
    # A more direct "family" model would be better for a "my kids" list.
    # As per revised instruction, we focus on chores created by parent and their assignments.

    return jsonify({
        'parent_id': parent.id,
        'username': parent.username,
        'chores_created': response_chores
    }), 200


@dashboard_bp.route('/api/kid/<int:kid_id>', methods=['GET'])
def get_kid_dashboard_api(kid_id):
    kid = User.query.get(kid_id)
    if not kid:
        return jsonify({'error': 'Kid user not found'}), 404
    if kid.role != 'kid':
        return jsonify({'error': 'User is not a kid'}), 403

    # Chores assigned to this kid that are 'pending' or other non-completed statuses
    # Using joinedload to efficiently fetch related Chore objects
    assigned_chores_data = []
    assignments = ChoreAssignment.query.options(joinedload(ChoreAssignment.chore))\
                                     .filter_by(user_id=kid.id)\
                                     .filter(ChoreAssignment.status != 'completed')\
                                     .order_by(ChoreAssignment.assigned_at.desc())\
                                     .all()

    for assignment in assignments:
        assigned_chores_data.append({
            'assignment_id': assignment.id,
            'chore_id': assignment.chore.id,
            'chore_name': assignment.chore.name,
            'chore_description': assignment.chore.description,
            'assigned_at': assignment.assigned_at.isoformat(),
            'status': assignment.status
        })
        
    return jsonify({
        'kid_id': kid.id,
        'username': kid.username,
        'pending_chores': assigned_chores_data
    }), 200

# ---- HTML Rendering View Functions ----

def fetch_parent_dashboard_data(parent_id):
    """ Helper function to fetch data for parent dashboard, callable by both API and HTML view """
    parent = User.query.get(parent_id)
    if not parent or parent.role != 'parent':
        return None, ('Parent user not found or user is not a parent', 404 if not parent else 403)

    chores_created_by_parent = Chore.query.filter_by(created_by_id=parent.id).order_by(Chore.id.desc()).all()
    
    chores_data = []
    for chore in chores_created_by_parent:
        assignments_list = []
        current_assignments = ChoreAssignment.query.filter_by(chore_id=chore.id).all()
        for assign in current_assignments:
            kid_user = User.query.get(assign.user_id)
            assignments_list.append({
                'assignment_id': assign.id,
                'kid_id': assign.user_id,
                'kid_username': kid_user.username if kid_user else 'Unknown Kid',
                'assigned_at': assign.assigned_at.isoformat(),
                'status': assign.status,
                'completed_at': assign.completed_at.isoformat() if assign.completed_at else None
            })
        chores_data.append({
            'chore_id': chore.id,
            'name': chore.name,
            'description': chore.description,
            'assignments': assignments_list,
            # include recurrence/rotation info if needed in template
            'is_recurring': chore.is_recurring,
            'recurrence_interval': chore.recurrence_interval,
            'next_due_date': chore.next_due_date.isoformat() if chore.next_due_date else None,
            'is_rotating': chore.is_rotating,
            'rotation_user_ids': chore.rotation_user_ids,
            'current_rotation_user_index': chore.current_rotation_user_index
        })
    
    return {
        'parent_id': parent.id,
        'username': parent.username,
        'chores_created': chores_data
    }, None


@dashboard_bp.route('/parent/<int:parent_id>', methods=['GET'])
def show_parent_dashboard(parent_id):
    parent_data, error = fetch_parent_dashboard_data(parent_id)
    if error:
        flash(error[0], 'error')
        return redirect(url_for('main_bp.index')) # Redirect to home or an error page

    # For the "Assign Chore" form, we need a list of all kids
    all_kids = User.query.filter_by(role='kid').all()
    
    return render_template('parent_dashboard.html', parent_info=parent_data, all_kids=all_kids)


def fetch_kid_dashboard_data(kid_id):
    """ Helper function to fetch data for kid dashboard """
    kid = User.query.get(kid_id)
    if not kid or kid.role != 'kid':
        return None, ('Kid user not found or user is not a kid', 404 if not kid else 403)

    assignments = ChoreAssignment.query.options(joinedload(ChoreAssignment.chore))\
                                     .filter_by(user_id=kid.id)\
                                     .filter(ChoreAssignment.status != 'completed')\
                                     .order_by(ChoreAssignment.assigned_at.desc())\
                                     .all()
    pending_chores_list = []
    for assignment in assignments:
        pending_chores_list.append({
            'assignment_id': assignment.id,
            'chore_id': assignment.chore.id,
            'chore_name': assignment.chore.name,
            'chore_description': assignment.chore.description,
            'assigned_at': assignment.assigned_at.isoformat(),
            'status': assignment.status
        })
    return {
        'kid_id': kid.id,
        'username': kid.username,
        'pending_chores': pending_chores_list
    }, None

@dashboard_bp.route('/kid/<int:kid_id>', methods=['GET'])
def show_kid_dashboard(kid_id):
    kid_data, error = fetch_kid_dashboard_data(kid_id)
    if error:
        flash(error[0], 'error')
        return redirect(url_for('main_bp.index'))

    return render_template('kid_dashboard.html', kid_info=kid_data)
