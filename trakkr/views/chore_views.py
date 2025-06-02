from flask import Blueprint, request, jsonify
from trakkr import db
from trakkr.models import Chore, User, ChoreAssignment
from datetime import datetime, date, timedelta

chore_bp = Blueprint('chore_bp', __name__, url_prefix='/chores')

@chore_bp.route('/create', methods=['POST'])
def create_chore():
    data = request.get_json()
    if not data or not data.get('name') or not data.get('created_by_id'):
        return jsonify({'error': 'Missing name or created_by_id'}), 400

    parent = User.query.get(data['created_by_id'])
    if not parent or parent.role != 'parent':
        return jsonify({'error': 'Invalid parent ID or user is not a parent'}), 400

    # Validate rotation_user_ids if provided
    rotation_user_ids = data.get('rotation_user_ids')
    if data.get('is_rotating') and (not rotation_user_ids or not isinstance(rotation_user_ids, list) or len(rotation_user_ids) == 0):
        return jsonify({'error': 'is_rotating is true but rotation_user_ids is missing, empty, or not a list.'}), 400
    
    if rotation_user_ids:
        for uid in rotation_user_ids:
            if not isinstance(uid, int):
                return jsonify({'error': 'All user IDs in rotation_user_ids must be integers.'}), 400
            kid_exists = User.query.filter_by(id=uid, role='kid').first()
            if not kid_exists:
                return jsonify({'error': f'User ID {uid} in rotation_user_ids is not a valid kid ID.'}), 400


    new_chore_data = {
        'name': data['name'],
        'description': data.get('description'),
        'created_by_id': parent.id,
        'is_recurring': data.get('is_recurring', False),
        'recurrence_interval': data.get('recurrence_interval'),
        'is_rotating': data.get('is_rotating', False),
        'rotation_user_ids': rotation_user_ids,
        'current_rotation_user_index': 0 if data.get('is_rotating') and rotation_user_ids else None
    }

    # Handle next_due_date
    if data.get('next_due_date'):
        try:
            new_chore_data['next_due_date'] = date.fromisoformat(data['next_due_date'])
        except ValueError:
            return jsonify({'error': 'Invalid next_due_date format. Use YYYY-MM-DD.'}), 400
    elif new_chore_data['is_recurring'] and new_chore_data['recurrence_interval']:
        # Auto-set next_due_date if recurring and not provided
        # For simplicity, setting it to today if not specified. Could be tomorrow.
        new_chore_data['next_due_date'] = date.today()


    new_chore = Chore(**new_chore_data)
    db.session.add(new_chore)
    db.session.flush() # Flush to get new_chore.id for assignment if needed

    # If rotating, assign to the first user in the list
    if new_chore.is_rotating and new_chore.rotation_user_ids:
        first_user_id = new_chore.rotation_user_ids[0]
        # User validation for this ID already happened above
        assignment = ChoreAssignment(
            chore_id=new_chore.id,
            user_id=first_user_id,
            # assigned_at is default
        )
        db.session.add(assignment)
        # The current_rotation_user_index is already 0, so it points to this user.

    db.session.commit()

    return jsonify({
        'message': 'Chore created successfully',
        'chore': {
            'id': new_chore.id,
            'name': new_chore.name,
            'description': new_chore.description,
            'created_by_id': new_chore.created_by_id,
            'is_recurring': new_chore.is_recurring,
            'recurrence_interval': new_chore.recurrence_interval,
            'next_due_date': new_chore.next_due_date.isoformat() if new_chore.next_due_date else None,
            'is_rotating': new_chore.is_rotating,
            'rotation_user_ids': new_chore.rotation_user_ids,
            'current_rotation_user_index': new_chore.current_rotation_user_index
        }
    }), 201

@chore_bp.route('/<int:chore_id>/assign', methods=['POST'])
def assign_chore(chore_id):
    data = request.get_json()
    if not data or not data.get('user_ids'):
        return jsonify({'error': 'Missing user_ids list'}), 400

    chore = Chore.query.get(chore_id)
    if not chore:
        return jsonify({'error': 'Chore not found'}), 404

    assigned_ids = data.get('user_ids', [])
    if not isinstance(assigned_ids, list):
        return jsonify({'error': 'user_ids must be a list'}), 400
    
    created_assignments = []
    errors = []

    for user_id in assigned_ids:
        kid = User.query.get(user_id)
        if not kid or kid.role != 'kid':
            errors.append({'user_id': user_id, 'error': 'Invalid kid ID or user is not a kid.'})
            continue

        # Check if this chore is already pending for this kid
        existing_assignment = ChoreAssignment.query.filter_by(
            chore_id=chore_id, 
            user_id=kid.id, 
            status='pending'
        ).first()

        if existing_assignment:
            errors.append({'user_id': user_id, 'error': f'Chore already pending for user {kid.username}.'})
            continue

        new_assignment = ChoreAssignment(
            chore_id=chore.id,
            user_id=kid.id
        )
        db.session.add(new_assignment)
        created_assignments.append(new_assignment)
    
    if created_assignments:
        db.session.commit()

    response_assignments = [{
        'id': ca.id,
        'chore_id': ca.chore_id,
        'user_id': ca.user_id,
        'assigned_at': ca.assigned_at.isoformat(),
        'status': ca.status
    } for ca in created_assignments]

    if errors:
        return jsonify({
            'message': 'Some assignments completed with errors.' if created_assignments else 'Assignments failed.',
            'created_assignments': response_assignments,
            'errors': errors
        }), 207 if created_assignments else 400
        
    return jsonify({
        'message': 'Chores assigned successfully',
        'assignments': response_assignments
    }), 201

@chore_bp.route('/assignments/<int:assignment_id>/complete', methods=['POST'])
def complete_chore_assignment(assignment_id):
    assignment = ChoreAssignment.query.get(assignment_id)
    if not assignment:
        return jsonify({'error': 'Chore assignment not found'}), 404

    if assignment.status == 'completed':
        return jsonify({'message': 'Chore already completed', 'assignment': {
            'id': assignment.id,
            'status': assignment.status,
            'completed_at': assignment.completed_at.isoformat() if assignment.completed_at else None
        }}), 200


    assignment.status = 'completed'
    assignment.completed_at = datetime.utcnow()
    
    chore = Chore.query.get(assignment.chore_id)
    if not chore:
        # This should ideally not happen if DB integrity is maintained
        db.session.rollback() # Rollback status change if chore is missing
        return jsonify({'error': 'Associated chore not found!'}), 500

    # Logic for rotating chores
    if chore.is_rotating and chore.rotation_user_ids and len(chore.rotation_user_ids) > 0:
        # Increment and loop rotation index
        chore.current_rotation_user_index = (chore.current_rotation_user_index + 1) % len(chore.rotation_user_ids)
        next_user_id = chore.rotation_user_ids[chore.current_rotation_user_index]
        
        # Check if this user already has a pending assignment for this chore (should ideally not happen if rotation is strict)
        existing_pending_assignment = ChoreAssignment.query.filter_by(
            chore_id=chore.id, 
            user_id=next_user_id, 
            status='pending'
        ).first()

        if not existing_pending_assignment:
            new_assignment = ChoreAssignment(
                chore_id=chore.id,
                user_id=next_user_id
            )
            db.session.add(new_assignment)
        else:
            # Handle case where next user already has a pending assignment (e.g. log, or skip)
            print(f"Info: Chore {chore.id} rotation to user {next_user_id} skipped, existing pending assignment found.")


    db.session.commit()

    return jsonify({
        'message': 'Chore marked as complete',
        'assignment': {
            'id': assignment.id,
            'chore_id': assignment.chore_id,
            'user_id': assignment.user_id,
            'status': assignment.status,
            'completed_at': assignment.completed_at.isoformat()
        },
        'next_rotation_user_index': chore.current_rotation_user_index if chore.is_rotating else None
    }), 200

@chore_bp.route('/trigger-recurring', methods=['POST'])
def trigger_recurring_chores():
    today = date.today()
    recurring_chores = Chore.query.filter(Chore.is_recurring == True, Chore.next_due_date <= today).all()
    
    actions_taken = []
    errors = []

    for chore in recurring_chores:
        action_log = {'chore_id': chore.id, 'name': chore.name, 'actions': []}

        # Determine assignees
        assignee_ids_to_set = set()
        if chore.is_rotating and chore.rotation_user_ids and len(chore.rotation_user_ids) > 0:
            # For rotating, assign to the current user in rotation
            # The rotation index should ideally be updated when the chore is completed or by another mechanism if it's also recurring.
            # For this trigger, we assume the current_rotation_user_index is correct for the *next* assignment.
            current_user_id = chore.rotation_user_ids[chore.current_rotation_user_index]
            assignee_ids_to_set.add(current_user_id)
            action_log['actions'].append(f'Identified rotating assignee: User ID {current_user_id}')
        else:
            # For non-rotating, re-assign to users from the most recent assignment(s) for this chore
            last_assignments = ChoreAssignment.query.filter_by(chore_id=chore.id)\
                                                .order_by(ChoreAssignment.assigned_at.desc())\
                                                .limit(len(User.query.filter_by(role='kid').all())) # Heuristic limit
            
            if last_assignments.count() > 0:
                # Get unique user_ids from the last cycle of assignments
                # This logic assumes that if a chore was assigned to multiple kids, they formed a "group" for that instance.
                # We find the most recent assignment time, then get all users assigned at that time.
                most_recent_time = last_assignments[0].assigned_at
                recent_user_ids = {ca.user_id for ca in ChoreAssignment.query.filter_by(chore_id=chore.id, assigned_at=most_recent_time).all()}
                assignee_ids_to_set.update(recent_user_ids)
                action_log['actions'].append(f'Identified past assignees: User IDs {recent_user_ids}')
            else:
                errors.append({'chore_id': chore.id, 'error': 'Recurring, non-rotating chore has no past assignments to derive next assignees.'})
                action_log['actions'].append('No past assignees found for non-rotating recurring chore.')
                continue # Skip to next chore

        if not assignee_ids_to_set:
            errors.append({'chore_id': chore.id, 'error': 'No assignees determined for recurring chore.'})
            action_log['actions'].append('No assignees could be determined.')
            continue

        # Create new assignments
        for user_id in assignee_ids_to_set:
            # Check for existing pending assignment for this user and chore
            existing_pending = ChoreAssignment.query.filter_by(chore_id=chore.id, user_id=user_id, status='pending').first()
            if not existing_pending:
                new_assignment = ChoreAssignment(chore_id=chore.id, user_id=user_id)
                db.session.add(new_assignment)
                action_log['actions'].append(f'Created new assignment for User ID {user_id}.')
            else:
                action_log['actions'].append(f'Skipped assignment for User ID {user_id}, existing pending assignment found.')

        # Update next_due_date
        if chore.recurrence_interval == 'daily':
            chore.next_due_date = today + timedelta(days=1)
        elif chore.recurrence_interval == 'weekly':
            chore.next_due_date = today + timedelta(weeks=1)
        elif chore.recurrence_interval == 'monthly':
            # This is simplified; real monthly might need more complex date math (e.g., same day next month)
            chore.next_due_date = today + timedelta(days=30) 
        else:
            errors.append({'chore_id': chore.id, 'error': f'Unknown recurrence_interval: {chore.recurrence_interval}'})
            action_log['actions'].append(f'Failed to update next_due_date due to unknown interval: {chore.recurrence_interval}.')
            continue # Don't commit this chore's session changes if interval is bad
        
        action_log['actions'].append(f'Updated next_due_date to {chore.next_due_date.isoformat()}.')
        actions_taken.append(action_log)

    if actions_taken or errors:
        db.session.commit()
        return jsonify({
            'message': 'Recurring chore trigger process completed.',
            'actions_taken': actions_taken,
            'errors': errors
        }), 200 if not errors else 207
    else:
        return jsonify({'message': 'No recurring chores due today or in the past.'}), 200
