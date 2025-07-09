from ansible_base.lib.routers import AssociationResourceRouter  # type: ignore

from pattern_service.core.views import (
    AutomationViewSet,
    ControllerLabelViewSet,
    PatternInstanceViewSet,
    PatternViewSet,
    TaskViewSet,
)

router = AssociationResourceRouter()
router.register(r"patterns", PatternViewSet, basename="pattern")
router.register(
    r"controllerlabels", ControllerLabelViewSet, basename="controllerlabel"
)
router.register(
    r"patterninstances", PatternInstanceViewSet, basename="patterninstance"
)
router.register(r"automations", AutomationViewSet, basename="automation")
router.register(r"tasks", TaskViewSet, basename="task")


urlpatterns = router.urls
