from .http import application
from .security import validate_config
from .storage import initialize
validate_config()
initialize()
