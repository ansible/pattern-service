from ansible_base.jwt_consumer.common.auth import JWTAuthentication


class PatternServiceJWTAuthentication(JWTAuthentication):
    use_rbac_permissions = True
