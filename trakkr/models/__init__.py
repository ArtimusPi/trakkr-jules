from trakkr import db
from .user import User
from .chore import Chore
from .chore_assignment import ChoreAssignment

# This file serves to make the models easily importable
# e.g., from trakkr.models import User, Chore, ChoreAssignment

# You can also define __all__ if you want to control what `from trakkr.models import *` imports
__all__ = ['User', 'Chore', 'ChoreAssignment', 'db']
