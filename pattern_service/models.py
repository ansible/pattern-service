from ansible_base.activitystream.models import AuditableModel
from ansible_base.lib.abstract_models import AbstractDABUser
from ansible_base.lib.abstract_models import AbstractOrganization
from ansible_base.lib.abstract_models import AbstractTeam
from ansible_base.lib.abstract_models import CommonModel
from ansible_base.rbac.permission_registry import permission_registry
from ansible_base.resource_registry.fields import AnsibleResourceField
from django.conf import settings
from django.db import models


class Organization(AbstractOrganization):
    class Meta:
        ordering = ["id"]
        permissions = [
            (
                "member_organization",
                "User is member of this organization",
            ),
        ]

    resource = AnsibleResourceField(primary_key_field="id")

    users: models.ManyToManyField = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="member_of_organizations",
        blank=True,
        help_text="The list of users on this organization",
    )

    admins: models.ManyToManyField = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="admin_of_organizations",
        blank=True,
        help_text="The list of admins for this organization",
    )

    extra_field: models.CharField = models.CharField(max_length=100, null=True)


class User(AbstractDABUser, CommonModel, AuditableModel):

    class Meta(AbstractDABUser.Meta):
        ordering = ["id"]

    resource = AnsibleResourceField(primary_key_field="id")
    activity_stream_excluded_field_names = ["last_login"]


class Team(AbstractTeam):
    resource = AnsibleResourceField(primary_key_field="id")

    class Meta:
        ordering = ["id"]
        abstract = False
        unique_together = [("organization", "name")]
        permissions = [("member_team", "Has all roles assigned to this team")]


permission_registry.register(Organization, parent_field_name=None)
permission_registry.register(Team)
