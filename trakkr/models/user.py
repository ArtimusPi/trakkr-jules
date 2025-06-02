from trakkr import db

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # Hashing will be implemented later
    role = db.Column(db.String(20), nullable=False)  # 'parent' or 'kid'

    # Relationships
    # For a parent, this could be chores they've created (linking through Chore.created_by_id)
    # For a kid, this is chores assigned to them (linking through ChoreAssignment.user_id)
    assigned_chores = db.relationship('ChoreAssignment', back_populates='user', lazy=True)
    created_chores = db.relationship('Chore', back_populates='creator', lazy=True)

    def __repr__(self):
        return f'<User {self.username}>'
