import pytest
import json
from trakkr.models import User, Chore, ChoreAssignment
from trakkr import db as main_db # To avoid fixture name conflict
from datetime import date, timedelta, datetime

# Helper to get user IDs from sample data
PARENT_ID = 1
KID1_ID = 2
KID2_ID = 3

@pytest.fixture
def setup_users_and_chores(db_session):
    """Fixture to ensure users and a basic chore setup for logic tests if sample data is not enough"""
    # Users are created by create_sample_data in conftest's db fixture.
    # We can rely on parent1 (ID 1), kid1 (ID 2), kid2 (ID 3) existing.
    parent = User.query.get(PARENT_ID)
    kid1 = User.query.get(KID1_ID)
    kid2 = User.query.get(KID2_ID)

    if not (parent and kid1 and kid2):
        pytest.skip("Base sample users not found, skipping logic tests that depend on them.")

    return parent, kid1, kid2


def test_chore_rotation_on_completion(client, db_session, setup_users_and_chores):
    parent, kid1, kid2 = setup_users_and_chores

    # Create a new rotating chore specifically for this test to avoid conflicts
    chore = Chore(
        name="Logic Test Rotating Chore",
        created_by_id=parent.id,
        is_rotating=True,
        rotation_user_ids=[kid1.id, kid2.id],
        current_rotation_user_index=0
    )
    db_session.add(chore)
    db_session.commit()

    # Initial assignment to kid1
    assignment1 = ChoreAssignment(chore_id=chore.id, user_id=kid1.id)
    db_session.add(assignment1)
    db_session.commit()
    assert chore.current_rotation_user_index == 0

    # Kid1 completes the chore
    response = client.post(f'/assignments/{assignment1.id}/complete')
    assert response.status_code == 200
    
    db_session.refresh(chore) # Refresh chore object from DB
    assert chore.current_rotation_user_index == 1 # Index should advance to kid2

    # Verify new assignment for kid2
    assignment2 = ChoreAssignment.query.filter_by(chore_id=chore.id, user_id=kid2.id, status='pending').first()
    assert assignment2 is not None
    assert assignment2.user_id == kid2.id

    # Kid2 completes the chore (assignment2.id would be the new one)
    response = client.post(f'/assignments/{assignment2.id}/complete')
    assert response.status_code == 200

    db_session.refresh(chore)
    assert chore.current_rotation_user_index == 0 # Index should loop back to kid1

    # Verify new assignment for kid1 again
    assignment3 = ChoreAssignment.query.filter_by(chore_id=chore.id, user_id=kid1.id, status='pending').first()
    assert assignment3 is not None
    assert assignment3.user_id == kid1.id
    
    # Clean up this specific chore and its assignments
    ChoreAssignment.query.filter_by(chore_id=chore.id).delete()
    db_session.delete(chore)
    db_session.commit()


def test_trigger_recurring_chore_daily_non_rotating(client, db_session, setup_users_and_chores):
    parent, kid1, _ = setup_users_and_chores

    chore_name = "Logic Test Daily Recurring"
    # Ensure chore doesn't exist from a previous failed run
    existing_chore = Chore.query.filter_by(name=chore_name).first()
    if existing_chore:
        ChoreAssignment.query.filter_by(chore_id=existing_chore.id).delete()
        db_session.delete(existing_chore)
        db_session.commit()

    # Create a daily recurring chore, due yesterday
    chore = Chore(
        name=chore_name,
        created_by_id=parent.id,
        is_recurring=True,
        recurrence_interval='daily',
        next_due_date=date.today() - timedelta(days=1)
    )
    db_session.add(chore)
    db_session.commit()

    # Initial assignment to kid1 (so the trigger knows who to assign to)
    initial_assignment = ChoreAssignment(chore_id=chore.id, user_id=kid1.id, status='completed', completed_at=datetime.utcnow()-timedelta(days=1))
    db_session.add(initial_assignment)
    db_session.commit()

    response = client.post('/chores/trigger-recurring')
    assert response.status_code == 200
    data = response.get_json()
    
    assert any(action_log['chore_id'] == chore.id and any('Created new assignment for User ID ' + str(kid1.id) in act for act in action_log['actions']) for action_log in data.get('actions_taken', [])), "Chore was not re-assigned to kid1"

    db_session.refresh(chore)
    assert chore.next_due_date == date.today() + timedelta(days=1) # Verify next_due_date updated

    # Verify new assignment exists
    new_assignment = ChoreAssignment.query.filter_by(chore_id=chore.id, user_id=kid1.id, status='pending').first()
    assert new_assignment is not None
    
    # Clean up
    ChoreAssignment.query.filter_by(chore_id=chore.id).delete()
    db_session.delete(chore)
    db_session.commit()

def test_trigger_recurring_chore_weekly_rotating(client, db_session, setup_users_and_chores):
    parent, kid1, kid2 = setup_users_and_chores
    chore_name = "Logic Test Weekly Rotating Recurring"

    # Ensure chore doesn't exist from a previous failed run
    existing_chore = Chore.query.filter_by(name=chore_name).first()
    if existing_chore:
        ChoreAssignment.query.filter_by(chore_id=existing_chore.id).delete()
        db_session.delete(existing_chore)
        db_session.commit()

    # Create a weekly recurring, rotating chore, due last week
    chore = Chore(
        name=chore_name,
        created_by_id=parent.id,
        is_recurring=True,
        recurrence_interval='weekly',
        next_due_date=date.today() - timedelta(days=7),
        is_rotating=True,
        rotation_user_ids=[kid1.id, kid2.id],
        current_rotation_user_index=0 # Starts with kid1
    )
    db_session.add(chore)
    db_session.commit()

    # Initial assignment (completed last week, so it's due now)
    initial_assignment = ChoreAssignment(
        chore_id=chore.id, 
        user_id=kid1.id, # Was kid1's turn
        status='completed', 
        completed_at=datetime.utcnow() - timedelta(days=7)
    )
    db_session.add(initial_assignment)
    db_session.commit()
    
    # When it was completed, the index should have rotated. Let's simulate that for the trigger.
    # Or, the trigger for rotating recurring chore assigns to current_rotation_user_index.
    # The problem description for trigger says: "if it's also a rotating chore, assign to the current_rotation_user_index user"
    # So current_rotation_user_index should be the one it's DUE for.

    response = client.post('/chores/trigger-recurring')
    assert response.status_code == 200
    data = response.get_json()

    # Check if the chore was processed and assigned to kid1 (index 0)
    assert any(action_log['chore_id'] == chore.id and any(f'Identified rotating assignee: User ID {kid1.id}' in act for act in action_log['actions']) for action_log in data.get('actions_taken', [])), "Chore was not identified for kid1"
    assert any(action_log['chore_id'] == chore.id and any(f'Created new assignment for User ID {kid1.id}' in act for act in action_log['actions']) for action_log in data.get('actions_taken', [])), "Chore was not re-assigned to kid1"


    db_session.refresh(chore)
    assert chore.next_due_date == date.today() + timedelta(weeks=1) # Verify next_due_date updated

    # Verify new assignment for kid1
    new_assignment = ChoreAssignment.query.filter_by(chore_id=chore.id, user_id=kid1.id, status='pending').first()
    assert new_assignment is not None
    
    # Clean up
    ChoreAssignment.query.filter_by(chore_id=chore.id).delete()
    db_session.delete(chore)
    db_session.commit()


def test_no_recurring_chores_due(client, db_session, setup_users_and_chores):
    parent, kid1, _ = setup_users_and_chores
    chore_name = "Logic Test No Recurring Due"
    # Ensure chore doesn't exist
    existing_chore = Chore.query.filter_by(name=chore_name).first()
    if existing_chore:
        ChoreAssignment.query.filter_by(chore_id=existing_chore.id).delete()
        db_session.delete(existing_chore)
        db_session.commit()

    chore = Chore(
        name=chore_name,
        created_by_id=parent.id,
        is_recurring=True,
        recurrence_interval='daily',
        next_due_date=date.today() + timedelta(days=1) # Due tomorrow
    )
    db_session.add(chore)
    db_session.commit()

    response = client.post('/chores/trigger-recurring')
    assert response.status_code == 200
    data = response.get_json()
    assert data['message'] == 'No recurring chores due today or in the past.'
    
    # Clean up
    db_session.delete(chore)
    db_session.commit()
