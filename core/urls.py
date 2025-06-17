from ansible_base.lib.routers import AssociationResourceRouter

from .views import PatternViewSet, ControllerLabelViewSet, PatternInstanceViewSet, AutomationViewSet


router = AssociationResourceRouter()
router.register(r'patterns', PatternViewSet, basename='pattern')
router.register(r'controllerlabels', ControllerLabelViewSet, basename='controllerlabel')
router.register(r'patterninstances', PatternInstanceViewSet, basename='patterninstance')
router.register(r'automations', AutomationViewSet, basename='automation')

urlpatterns = router.urls
