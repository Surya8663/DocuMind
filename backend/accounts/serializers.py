from rest_framework_simplejwt.serializers import TokenObtainPairSerializer


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    Custom JWT Serializer that injects tenant_id and role into the token claims.
    This prevents downstream services from needing to query the database to know
    a user's tenant or access level.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)

        # Add custom claims
        token["role"] = user.role

        # Superusers might not have a tenant
        if user.tenant_id:
            token["tenant_id"] = str(user.tenant_id)
        else:
            token["tenant_id"] = None

        return token
