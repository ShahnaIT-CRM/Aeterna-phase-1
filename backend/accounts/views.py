from rest_framework import permissions, status, viewsets
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .models import Certification, EmploymentHistory, Qualification
from .permissions import IsInstitute, IsTeacher
from .serializers import (
    CertificationSerializer, EmploymentHistorySerializer, InstituteProfileSerializer,
    QualificationSerializer, RegisterSerializer, TeacherProfileSerializer,
)


def user_payload(user):
    if user.role == "teacher":
        name = user.teacher_profile.full_name
    elif user.role == "institute":
        name = user.institute_profile.name
    else:
        name = "Admin"
    return {"id": user.id, "email": user.email, "role": user.role, "display_name": name}


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        s = RegisterSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = s.save()
        refresh = RefreshToken.for_user(user)
        return Response(
            {"user": user_payload(user), "access": str(refresh.access_token), "refresh": str(refresh)},
            status=status.HTTP_201_CREATED,
        )


class MeView(APIView):
    def get(self, request):
        return Response(user_payload(request.user))


class TeacherProfileView(RetrieveUpdateAPIView):
    serializer_class = TeacherProfileSerializer
    permission_classes = [IsTeacher]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_object(self):
        return self.request.user.teacher_profile


class InstituteProfileView(RetrieveUpdateAPIView):
    serializer_class = InstituteProfileSerializer
    permission_classes = [IsInstitute]
    http_method_names = ["get", "patch", "put", "head", "options"]

    def get_object(self):
        return self.request.user.institute_profile


class _TeacherOwnedViewSet(viewsets.ModelViewSet):
    permission_classes = [IsTeacher]
    model = None

    def get_queryset(self):
        return self.model.objects.filter(teacher=self.request.user.teacher_profile)

    def perform_create(self, serializer):
        serializer.save(teacher=self.request.user.teacher_profile)


class QualificationViewSet(_TeacherOwnedViewSet):
    model = Qualification
    serializer_class = QualificationSerializer


class CertificationViewSet(_TeacherOwnedViewSet):
    model = Certification
    serializer_class = CertificationSerializer


class EmploymentViewSet(_TeacherOwnedViewSet):
    model = EmploymentHistory
    serializer_class = EmploymentHistorySerializer
