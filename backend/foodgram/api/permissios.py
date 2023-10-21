from rest_framework import permissions


class IsAdminOrAuthorOrReadOnly(permissions.BasePermission):

    def has_object_permission(self, request, view, object):
        return (
            request.method in permissions.SAFE_METHODS
            or object.author == request.user
            or request.user.is_staff
        )
