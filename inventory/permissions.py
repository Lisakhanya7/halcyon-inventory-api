from rest_framework.permissions import BasePermission, SAFE_METHODS


class StaffWriteOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (
            request.method in SAFE_METHODS or request.user.is_staff
        ))


class IsOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user.is_staff or obj.created_by_id == request.user.id
