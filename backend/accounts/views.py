from rest_framework import status, generics, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from django.contrib.auth import authenticate
from django.db.models import Q
from drf_spectacular.utils import extend_schema, extend_schema_view
from .models import User, Experience, Education, UserSkill
from .serializers import (
    UserRegistrationSerializer,
    UserLoginSerializer,
    UserProfileSerializer,
    UserProfileUpdateSerializer,
    UserBasicSerializer,
    UserSearchSerializer,
    ExperienceSerializer,
    EducationSerializer,
    UserSkillSerializer,
    ChangePasswordSerializer,
    UserLogoutSerializer,
)


class UserRegistrationView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Registration successful'
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data['user']
        
        # Generate tokens
        refresh = RefreshToken.for_user(user)
        
        return Response({
            'user': UserProfileSerializer(user).data,
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'message': 'Login successful'
        })


class UserLogoutView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = UserLogoutSerializer
    
    def post(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            refresh_token = serializer.validated_data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    
    def update(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not user.check_password(old_password):
            return Response({'error': 'Invalid old password'}, status=status.HTTP_400_BAD_REQUEST)
        
        user.set_password(new_password)
        user.save()
        
        return Response({'message': 'Password changed successfully'})


class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(is_active=True)
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action in ['update', 'partial_update']:
            return UserProfileUpdateSerializer
        elif self.action == 'list':
            return UserBasicSerializer
        return UserProfileSerializer
    
    def get_queryset(self):
        if self.action == 'list':
            # For listing users (discovery), exclude current user and show only public profiles
            return User.objects.filter(
                is_active=True,
                privacy_public_profile=True
            ).exclude(id=self.request.user.id)
        return super().get_queryset()
    
    def get_object(self):
        if self.action in ['update', 'partial_update']:
            return self.request.user
        return super().get_object()


class UserSearchView(generics.ListAPIView):
    serializer_class = UserSearchSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        query = self.request.query_params.get('q', '')
        if not query:
            return User.objects.none()
        
        return User.objects.filter(
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(headline__icontains=query) |
            Q(current_position__icontains=query) |
            Q(industry__icontains=query),
            is_active=True,
            privacy_public_profile=True
        ).exclude(id=self.request.user.id)[:20]


@extend_schema_view(
    list=extend_schema(description='List experiences for the current user'),
    create=extend_schema(description='Create a new experience'),
    update=extend_schema(description='Update an experience'),
    destroy=extend_schema(description='Delete an experience')
)
class ExperienceViewSet(viewsets.ModelViewSet):
    serializer_class = ExperienceSerializer
    permission_classes = [IsAuthenticated]
    queryset = Experience.objects.none()  # Default empty queryset
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # for schema generation
            return Experience.objects.none()
        return Experience.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(description='List education entries for the current user'),
    create=extend_schema(description='Create a new education entry'),
    update=extend_schema(description='Update an education entry'),
    destroy=extend_schema(description='Delete an education entry')
)
class EducationViewSet(viewsets.ModelViewSet):
    serializer_class = EducationSerializer
    permission_classes = [IsAuthenticated]
    queryset = Education.objects.none()  # Default empty queryset
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # for schema generation
            return Education.objects.none()
        return Education.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


@extend_schema_view(
    list=extend_schema(description='List skills for the current user'),
    create=extend_schema(description='Create a new skill'),
    update=extend_schema(description='Update a skill'),
    destroy=extend_schema(description='Delete a skill')
)
class UserSkillViewSet(viewsets.ModelViewSet):
    serializer_class = UserSkillSerializer
    permission_classes = [IsAuthenticated]
    queryset = UserSkill.objects.none()  # Default empty queryset
    
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):  # for schema generation
            return UserSkill.objects.none()
        return UserSkill.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user) 