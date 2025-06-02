import pytest
from trakkr.models import User, Chore, ChoreAssignment
from trakkr import db as main_db # Renamed to avoid conflict with fixture
from datetime import datetime, date

# User Model Tests
def test_user_creation(db_session): # Use db_session fixture
    # Sample data creates user1 (parent), user2 (kid), user3 (kid)
    parent = User.query.get(1)
    assert parent is not None
    assert parent.username == 'parent1'
    assert parent.role == 'parent'
    assert parent.password_hash is not None # Assuming create_sample_data sets a hash

    kid = User.query.get(2)
    assert kid is not None
    assert kid.username == 'kid1'
    assert kid.role == 'kid'

    # Test creating a new user
    new_user = User(username='test_user_model', password_hash='somehash', role='kid')
    db_session.add(new_user)
    db_session.commit()
    assert new_user.id is not None
    retrieved_user = User.query.filter_by(username='test_user_model').first()
    assert retrieved_user.role == 'kid'

# Chore Model Tests
def test_chore_creation(db_session):
    parent = User.query.get(1) # Assuming parent1 (ID 1) exists from sample data
    assert parent is not None, "Test setup issue: Parent user with ID 1 not found."

    chore_name = "Model Test Chore"
    chore = Chore(
        name=chore_name,
        description="A chore for model testing.",
        created_by_id=parent.id,
        is_recurring=True,
        recurrence_interval='daily',
        next_due_date=date.today(),
        is_rotating=False
    )
    db_session.add(chore)
    db_session.commit()

    assert chore.id is not None
    retrieved_chore = Chore.query.filter_by(name=chore_name).first()
    assert retrieved_chore is not None
    assert retrieved_chore.creator == parent
    assert retrieved_chore.is_recurring is True
    assert retrieved_chore.recurrence_interval == 'daily'
    assert retrieved_chore.is_rotating is False
    assert retrieved_chore.description == "A chore for model testing."

# ChoreAssignment Model Tests
def test_chore_assignment_creation(db_session):
    parent = User.query.get(1)
    kid = User.query.get(2)
    assert parent is not None and kid is not None, "Test setup issue: Parent or Kid user not found."

    chore = Chore(name="Assignment Test Chore", created_by_id=parent.id)
    db_session.add(chore)
    db_session.commit() # Commit chore to get its ID

    assignment = ChoreAssignment(
        chore_id=chore.id,
        user_id=kid.id
    )
    db_session.add(assignment)
    db_session.commit()

    assert assignment.id is not None
    retrieved_assignment = ChoreAssignment.query.get(assignment.id)
    assert retrieved_assignment is not None
    assert retrieved_assignment.chore == chore
    assert retrieved_assignment.user == kid
    assert retrieved_assignment.status == 'pending' # Default status
    assert isinstance(retrieved_assignment.assigned_at, datetime)

    # Test relationships from User and Chore side
    assert chore in parent.created_chores # This relationship was 'created_chores' on User model
    assert assignment in kid.assigned_chores
    assert assignment in chore.assignments

def test_rotating_chore_model_fields(db_session):
    parent = User.query.get(1)
    kid1 = User.query.get(2)
    kid2 = User.query.get(3)
    assert parent and kid1 and kid2, "Sample users not found for rotating chore model test"

    rotating_chore = Chore(
        name="Rotating Model Test Chore",
        created_by_id=parent.id,
        is_rotating=True,
        rotation_user_ids=[kid1.id, kid2.id],
        current_rotation_user_index=0
    )
    db_session.add(rotating_chore)
    db_session.commit()

    retrieved_chore = Chore.query.filter_by(name="Rotating Model Test Chore").first()
    assert retrieved_chore is not None
    assert retrieved_chore.is_rotating is True
    assert retrieved_chore.rotation_user_ids == [kid1.id, kid2.id]
    assert retrieved_chore.current_rotation_user_index == 0
