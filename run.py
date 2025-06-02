from trakkr import app, db
from trakkr.models import User, Chore, ChoreAssignment # Import models
import os
from datetime import date, timedelta

def create_tables_if_needed():
    # Get the database URI from the app's config
    db_uri = app.config.get('SQLALCHEMY_DATABASE_URI')
    if db_uri:
        # For SQLite, the database is a file. Check if it exists.
        if db_uri.startswith('sqlite:///'):
            db_path = db_uri.split('sqlite:///')[1]
            if not os.path.exists(db_path):
                print(f"Database file not found at {db_path}. Creating tables...")
                with app.app_context():
                    db.create_all()
                print("Tables created.")
            else:
                print(f"Database file found at {db_path}.")
        else:
            # For other databases, you might need a different check or just run create_all()
            # For simplicity, we'll assume non-SQLite DBs are managed externally or create_all is safe.
            # print("Non-SQLite database detected. Consider manual schema management or ensure create_all() is safe.")
            # with app.app_context():
            #     db.create_all() # Be cautious with this in production for non-SQLite DBs
            pass # For now, do nothing for non-SQLite, assumes it's handled.

def create_sample_data():
    with app.app_context():
        users_to_create = [
            {'id': 1, 'username': 'parent1', 'password_hash': 'hashed_password_parent1', 'role': 'parent'},
            {'id': 2, 'username': 'kid1', 'password_hash': 'hashed_password_kid1', 'role': 'kid'},
            {'id': 3, 'username': 'kid2', 'password_hash': 'hashed_password_kid2', 'role': 'kid'},
        ]

        created_users = {} # To store successfully created or found users by their intended ID

        for user_data in users_to_create:
            user = User.query.get(user_data['id'])
            if not user:
                # No user with this ID, try to create with this ID
                # This might fail if the DB doesn't allow specifying IDs that are normally auto-incremented,
                # or if another user already exists with a different ID but same username.
                # For SQLite, manually setting an integer primary key is generally allowed if it's not taken.
                try_user = User.query.filter_by(username=user_data['username']).first()
                if try_user:
                    print(f"User with username {user_data['username']} already exists with ID {try_user.id}. Cannot create with ID {user_data['id']}.")
                    created_users[user_data['id']] = try_user # Store the found user
                    continue
                
                print(f"Creating user: {user_data['username']} with ID {user_data['id']}")
                user = User(id=user_data['id'], 
                            username=user_data['username'], 
                            password_hash=user_data['password_hash'], 
                            role=user_data['role'])
                db.session.add(user)
                db.session.commit()
                created_users[user_data['id']] = user
            elif user.username == user_data['username'] and user.role == user_data['role']:
                print(f"User {user_data['username']} (ID: {user_data['id']}) already exists with correct details.")
                created_users[user_data['id']] = user
            else:
                print(f"User with ID {user_data['id']} already exists but with different details (Username: {user.username}, Role: {user.role}). Skipping creation for {user_data['username']}.")
                # We might not want to use this user if details don't match, handle as needed.
                # For now, we'll add them to created_users if found, but chore creation might use wrong user.
                created_users[user_data['id']] = user


        parent1 = created_users.get(1)
        kid1 = created_users.get(2)
        kid2 = created_users.get(3)

        if not parent1 or parent1.role != 'parent': # Extra check
            print("Critical: Parent1 (ID 1) could not be confirmed or is not a parent. Aborting further sample data creation.")
            return
        
        # Sample Chore 1 (Normal)
        chore1_name = 'Test Chore 1 (Normal)'
        if Chore.query.filter_by(name=chore1_name).first() is None:
            print(f"Creating sample chore: '{chore1_name}' for {parent1.username}")
            chore1 = Chore(name=chore1_name, description='A sample normal chore.', created_by_id=parent1.id)
            db.session.add(chore1)
            if kid1: # Check if kid1 was successfully retrieved/created
                assign1 = ChoreAssignment(chore=chore1, user_id=kid1.id) # Use relationship or chore_id
                db.session.add(assign1)
            db.session.commit()
        else:
            print(f"Chore '{chore1_name}' already exists.")

        chore2_name = 'Test Chore 2 (Rotating)'
        if Chore.query.filter_by(name=chore2_name).first() is None and kid1 and kid2:
            print(f"Creating sample rotating chore: '{chore2_name}' for {parent1.username}, between {kid1.username} and {kid2.username}.")
            chore2 = Chore(
                name=chore2_name, description='A sample rotating chore.', created_by_id=parent1.id,
                is_rotating=True, rotation_user_ids=[kid1.id, kid2.id], current_rotation_user_index=0
            )
            db.session.add(chore2)
            # Initial assignment for rotating chore
            assign_rot = ChoreAssignment(chore=chore2, user_id=kid1.id)
            db.session.add(assign_rot)
            db.session.commit()
        elif not (kid1 and kid2):
             print(f"Could not create '{chore2_name}' because one or both sample kids are missing or not confirmed.")
        else:
            print(f"Chore '{chore2_name}' already exists.")

        chore3_name = 'Test Chore 3 (Recurring Daily)'
        if Chore.query.filter_by(name=chore3_name).first() is None and kid1:
            print(f"Creating sample recurring daily chore: '{chore3_name}' for {parent1.username}, assigned to {kid1.username}.")
            chore3 = Chore(
                name=chore3_name, description='A sample daily recurring chore.', created_by_id=parent1.id,
                is_recurring=True, recurrence_interval='daily', next_due_date=date.today()
            )
            db.session.add(chore3)
            assign_rec = ChoreAssignment(chore=chore3, user_id=kid1.id)
            db.session.add(assign_rec)
            db.session.commit()
        elif not kid1:
            print(f"Could not create '{chore3_name}' because kid1 is missing or not confirmed.")
        else:
            print(f"Chore '{chore3_name}' already exists.")
            
        chore4_name = 'Test Chore 4 (Weekly Rotating)'
        if Chore.query.filter_by(name=chore4_name).first() is None and kid1 and kid2:
            print(f"Creating sample weekly rotating chore: '{chore4_name}' for {parent1.username}, between {kid1.username} & {kid2.username}.")
            chore4 = Chore(
                name=chore4_name, description='A sample weekly rotating chore.', created_by_id=parent1.id,
                is_recurring=True, recurrence_interval='weekly', next_due_date=date.today() - timedelta(days=1),
                is_rotating=True, rotation_user_ids=[kid1.id, kid2.id], current_rotation_user_index=0
            )
            db.session.add(chore4)
            assign_rec_rot = ChoreAssignment(chore=chore4, user_id=kid1.id)
            db.session.add(assign_rec_rot)
            db.session.commit()
        elif not (kid1 and kid2):
            print(f"Could not create '{chore4_name}' because one or both sample kids are missing or not confirmed.")
        else:
            print(f"Chore '{chore4_name}' already exists.")
        
        print("Sample data creation process complete.")


if __name__ == '__main__':
    create_tables_if_needed()
    create_sample_data() # Add call to create sample data
    app.run(debug=True)
