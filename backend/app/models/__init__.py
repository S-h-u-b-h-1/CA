import inspect

from app.core.database import Base
from app.models import models as _models

# Re-export every SQLAlchemy model class defined in app.models.models automatically,
# rather than a hand-maintained list, so this package can never silently fall out of
# sync with new models again (it previously only exported 28 of 69 models).
_model_classes = {
    name: obj
    for name, obj in vars(_models).items()
    if inspect.isclass(obj) and issubclass(obj, Base) and obj is not Base
}

globals().update(_model_classes)

__all__ = ["Base"] + sorted(_model_classes.keys())
