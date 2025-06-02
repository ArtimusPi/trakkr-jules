import pytest
import json
from trakkr.models import User, Chore, ChoreAssignment
from trakkr import db as main_db # To avoid fixture name conflict
from datetime import date

# Helper to get user IDs from sample data
PARENT_ID = 1
KID1_ID = 2
KID2_ID = 3

def test_create_chore_api_success(client):
    response = client.post('/chores/create', json={
        'name': 'API Test Chore',
        'description': 'Created via API test',
        'created_by_id': PARENT_ID
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'Chore created successfully'
    assert data['chore']['name'] == 'API Test Chore'
    
    # Verify in DB
    chore = Chore.query.filter_by(name='API Test Chore').first()
    assert chore is not None
    assert chore.created_by_id == PARENT_ID

def test_create_chore_api_missing_name(client):
    response = client.post('/chores/create', json={
        'description': 'Missing name test',
        'created_by_id': PARENT_ID
    })
    assert response.status_code == 400
    data = response.get_json()
    assert 'Missing name or created_by_id' in data['error']

def test_create_chore_api_invalid_parent(client):
    response = client.post('/chores/create', json={
        'name': 'Kid Create Chore Test',
        'created_by_id': KID1_ID # Kid trying to create
    })
    assert response.status_code == 400 # Or 403 depending on implementation
    data = response.get_json()
    assert 'Invalid parent ID or user is not a parent' in data['error']

def test_assign_chore_api_success(client):
    # First, create a chore to assign
    chore = Chore(name='Chore To Assign API', created_by_id=PARENT_ID)
    main_db.session.add(chore)
    main_db.session.commit()

    response = client.post(f'/chores/{chore.id}/assign', json={
        'user_ids': [KID1_ID, KID2_ID]
    })
    assert response.status_code == 201
    data = response.get_json()
    assert data['message'] == 'Chores assigned successfully'
    assert len(data['assignments']) == 2
    
    assignments = ChoreAssignment.query.filter_by(chore_id=chore.id).all()
    assert len(assignments) == 2
    assigned_user_ids = {a.user_id for a in assignments}
    assert KID1_ID in assigned_user_ids
    assert KID2_ID in assigned_user_ids

def test_assign_chore_api_chore_not_found(client):
    response = client.post('/chores/9999/assign', json={'user_ids': [KID1_ID]})
    assert response.status_code == 404

def test_assign_chore_api_kid_not_found(client, db_session):
    chore = Chore.query.filter_by(name='Test Chore 1 (Normal)').first() # From sample data
    assert chore is not None, "Sample chore 'Test Chore 1 (Normal)' not found"
    
    response = client.post(f'/chores/{chore.id}/assign', json={'user_ids': [9999]}) # Non-existent kid
    assert response.status_code == 207 # Partial success or error, depending on API
    data = response.get_json()
    assert 'Assignments failed.' in data['message'] or 'Some assignments completed with errors.' in data['message']
    assert any(err['error'] == 'Invalid kid ID or user is not a kid.' for err in data.get('errors', []))


def test_complete_chore_assignment_api(client, db_session):
    # Find an existing assignment from sample data or create one
    # Sample data creates 'Test Chore 1 (Normal)' and assigns to kid1 (ID 2)
    chore = Chore.query.filter_by(name='Test Chore 1 (Normal)').first()
    assert chore is not None
    assignment = ChoreAssignment.query.filter_by(chore_id=chore.id, user_id=KID1_ID, status='pending').first()
    
    if not assignment: # If sample data didn't create it or it was completed
        chore_for_completion_test = Chore(name='ChoreForCompletionAPI', created_by_id=PARENT_ID)
        db_session.add(chore_for_completion_test)
        db_session.commit()
        assignment = ChoreAssignment(chore_id=chore_for_completion_test.id, user_id=KID1_ID)
        db_session.add(assignment)
        db_session.commit()

    assert assignment is not None, "No pending assignment found for KID1_ID to test completion."
    assert assignment.status == 'pending'

    response = client.post(f'/assignments/{assignment.id}/complete')
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'Chore marked as complete'
    assert data['assignment']['status'] == 'completed'
    
    completed_assignment = ChoreAssignment.query.get(assignment.id)
    assert completed_assignment.status == 'completed'
    assert completed_assignment.completed_at is not None

def test_parent_dashboard_api_success(client):
    response = client.get(f'/dashboards/api/parent/{PARENT_ID}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['parent_id'] == PARENT_ID
    assert 'chores_created' in data

def test_parent_dashboard_api_not_parent(client):
    response = client.get(f'/dashboards/api/parent/{KID1_ID}') # Kid ID trying to access parent dash
    assert response.status_code == 403 # Forbidden

def test_kid_dashboard_api_success(client):
    response = client.get(f'/dashboards/api/kid/{KID1_ID}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['kid_id'] == KID1_ID
    assert 'pending_chores' in data

def test_kid_dashboard_api_not_kid(client):
    response = client.get(f'/dashboards/api/kid/{PARENT_ID}') # Parent ID trying to access kid dash
    assert response.status_code == 403 # Forbidden

def test_kid_dashboard_api_no_pending_chores(client, db_session):
    # Create a new kid with no chores
    new_kid = User(id=98, username='kid_no_chores', password_hash='pw', role='kid')
    db_session.add(new_kid)
    db_session.commit()
    
    response = client.get(f'/dashboards/api/kid/{new_kid.id}')
    assert response.status_code == 200
    data = response.get_json()
    assert data['kid_id'] == new_kid.id
    assert len(data['pending_chores']) == 0
    
    # Clean up the new kid
    db_session.delete(new_kid)
    db_session.commit()

# Test for creating a rotating chore via API
def test_create_rotating_chore_api(client):
    response = client.post('/chores/create', json={
        'name': 'API Rotating Chore',
        'created_by_id': PARENT_ID,
        'is_rotating': True,
        'rotation_user_ids': [KID1_ID, KID2_ID]
    })
    assert response.status_code == 201
    data = response.get_json()['chore']
    assert data['is_rotating'] is True
    assert data['rotation_user_ids'] == [KID1_ID, KID2_ID]
    assert data['current_rotation_user_index'] == 0 # Should be assigned to first user

    # Verify initial assignment
    chore_id = data['id']
    assignment = ChoreAssignment.query.filter_by(chore_id=chore_id, user_id=KID1_ID).first()
    assert assignment is not None
    assert assignment.status == 'pending'

# Test for creating a recurring chore via API
def test_create_recurring_chore_api(client):
    today_iso = date.today().isoformat()
    response = client.post('/chores/create', json={
        'name': 'API Recurring Chore',
        'created_by_id': PARENT_ID,
        'is_recurring': True,
        'recurrence_interval': 'weekly',
        'next_due_date': today_iso
    })
    assert response.status_code == 201
    data = response.get_json()['chore']
    assert data['is_recurring'] is True
    assert data['recurrence_interval'] == 'weekly'
    assert data['next_due_date'] == today_iso

    # Verify in DB
    chore = Chore.query.filter_by(name='API Recurring Chore').first()
    assert chore is not None
    assert chore.next_due_date == date.today()
