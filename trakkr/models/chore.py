from trakkr import db

class Chore(db.Model):
    __tablename__ = 'chores'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    creator = db.relationship('User', back_populates='created_chores')

    assignments = db.relationship('ChoreAssignment', back_populates='chore', lazy=True, cascade="all, delete-orphan")

    # Recurring chore fields
    is_recurring = db.Column(db.Boolean, default=False, nullable=False)
    recurrence_interval = db.Column(db.String(20), nullable=True)  # 'daily', 'weekly', 'monthly'
    next_due_date = db.Column(db.Date, nullable=True)

    # Rotating chore fields
    is_rotating = db.Column(db.Boolean, default=False, nullable=False)
    # Storing as JSON. Ensure your DB supports JSON type or use Text and handle serialization/deserialization.
    # For SQLite, JSON type is available in newer versions and handled by SQLAlchemy.
    rotation_user_ids = db.Column(db.JSON, nullable=True) # List of user IDs
    current_rotation_user_index = db.Column(db.Integer, default=0, nullable=True)


    def __repr__(self):
        return f'<Chore {self.name} - Recurring: {self.is_recurring}, Rotating: {self.is_rotating}>'
