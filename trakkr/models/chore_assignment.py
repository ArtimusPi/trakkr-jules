from trakkr import db
from datetime import datetime

class ChoreAssignment(db.Model):
    __tablename__ = 'chore_assignments'

    id = db.Column(db.Integer, primary_key=True)
    chore_id = db.Column(db.Integer, db.ForeignKey('chores.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False) # Kid assigned the chore

    assigned_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    status = db.Column(db.String(20), nullable=False, default='pending') # 'pending', 'completed', 'overdue'

    chore = db.relationship('Chore', back_populates='assignments')
    user = db.relationship('User', back_populates='assigned_chores')

    def __repr__(self):
        return f'<ChoreAssignment {self.chore.name} for {self.user.username} - {self.status}>'
