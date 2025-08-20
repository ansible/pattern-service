from ansible_base.lib.routers import AssociationResourceRouter

from .views import AutomationViewSet
from .views import ControllerLabelViewSet
from .views import PatternInstanceViewSet
from .views import PatternViewSet
from .views import TaskViewSet

router = AssociationResourceRouter()
router.register(r"patterns", PatternViewSet, basename="pattern")
router.register(
    r"controller_labels", ControllerLabelViewSet, basename="controller_label"
)
router.register(
    r"pattern_instances", PatternInstanceViewSet, basename="pattern_instance"
)
router.register(r"automations", AutomationViewSet, basename="automation")
router.register(r"tasks", TaskViewSet, basename="task")

urlpatterns = router.urls
