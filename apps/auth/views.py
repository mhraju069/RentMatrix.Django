from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.db.models import Q
from drf_spectacular.utils import extend_schema, OpenApiResponse
from .models import User, OTP, Document
from .utils import send_otp, format_serializer_errors
from .serializers import (
    CreateUserSerializer, LoginUserSerializer, GetOtpSerializer, VerifyOtpSerializer,
    UpdateUserSerializer, ResetPasswordSerializer, UploadDocumentSerializer, UserDataSerializer,
    MultipleUploadDocumentSerializer
)

def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)
    # The custom logic requires access_token, refresh_token
    return {
        'refresh_token': str(refresh),
        'access_token': str(refresh.access_token),
    }

class SignupView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=CreateUserSerializer)
    def post(self, request):
        serializer = CreateUserSerializer(data=request.data)
        if serializer.is_valid():
            if User.objects.filter(email=serializer.validated_data['email']).exists():
                return Response({"status": 400, "success": False, "message": "User with this email already exists"}, status=status.HTTP_400_BAD_REQUEST)
            if User.objects.filter(phone=serializer.validated_data['phone']).exists():
                return Response({"status": 400, "success": False, "message": "User with this phone already exists"}, status=status.HTTP_400_BAD_REQUEST)
            
            user = serializer.save()
            user.set_password(serializer.validated_data['password'])
            user.save()

            send_otp(user, "signup")
            
            return Response({
                "status": 201, "success": True, "message": "User created successfully",
            }, status=status.HTTP_201_CREATED)
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=LoginUserSerializer, responses={200: UserDataSerializer})
    def post(self, request):
        serializer = LoginUserSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data.get('email')
            phone = serializer.validated_data.get('phone')
            password = serializer.validated_data.get('password')

            user = User.objects.filter(Q(email=email) | Q(phone=phone)).first()
            
            if not user:
                return Response({"status": 404, "success": False, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            if not user.is_active:
                return Response({"status": 403, "success": False, "message": "Your account is inactive."}, status=status.HTTP_403_FORBIDDEN)
            if getattr(user, 'block', False):
                return Response({"status": 403, "success": False, "message": "Your account has been blocked."}, status=status.HTTP_403_FORBIDDEN)
            if not user.check_password(password):
                return Response({"status": 401, "success": False, "message": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
            
            tokens = get_tokens_for_user(user)
            user_data = UserDataSerializer(user).data
            
            return Response({
                "status": 200, "success": True, "message": "User logged in successfully",
                "user": user_data, **tokens
            }, status=status.HTTP_200_OK)
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: UserDataSerializer})
    def get(self, request):
        user_data = UserDataSerializer(request.user).data
        return Response({"status": 200, "success": True, "message": "User fetched successfully", "user": user_data})

class MeUpdateView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=UpdateUserSerializer, responses={200: UserDataSerializer})
    def patch(self, request):
        user = request.user
        serializer = UpdateUserSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            data = serializer.validated_data
            if 'name' in data:
                user.name = data['name']
            if 'phone' in data:
                user.phone = data['phone']
            if 'new_password' in data:
                old_password = data.get('old_password')
                new_password = data.get('new_password')
                if not old_password or not new_password:
                    return Response({"success": False, "message": "Old and new password are required"}, status=status.HTTP_400_BAD_REQUEST)
                if not user.check_password(old_password):
                    return Response({"success": False, "message": "Invalid old password"}, status=status.HTTP_400_BAD_REQUEST)
                user.set_password(new_password)
            
            image = request.FILES.get('image')
            if image:
                if not image.content_type.startswith("image/"):
                    return Response({"success": False, "message": "Uploaded file is not a valid image"}, status=status.HTTP_400_BAD_REQUEST)
                user.image = image
            
            user.save()
            user_data = UserDataSerializer(user).data
            return Response({"status": 200, "success": True, "message": "User updated successfully", "user": user_data})
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)


class GetOtpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = GetOtpSerializer

    @extend_schema(request=GetOtpSerializer)
    def post(self, request):
        serializer = GetOtpSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"status": 404, "success": False, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            res = send_otp(user)
            if res:
                return Response({"status": 200, "success": True, "message": "Otp sent successfully"})
            else:
                return Response({"status": 500, "success": False, "message": "Otp not sent"})
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

class VerifyOtpView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    serializer_class = VerifyOtpSerializer

    @extend_schema(request=VerifyOtpSerializer, responses={200: UserDataSerializer})
    def post(self, request):
        serializer = VerifyOtpSerializer(data=request.data)
        if serializer.is_valid():
            email = serializer.validated_data['email']
            otp = serializer.validated_data['otp']
            
            user = User.objects.filter(email=email).first()
            if not user:
                return Response({"status": 404, "success": False, "message": "User not found"}, status=status.HTTP_404_NOT_FOUND)
            
            otp_code = OTP.objects.filter(user=user).first()
            if not otp_code:
                return Response({"status": 404, "success": False, "message": "OTP not found"}, status=status.HTTP_404_NOT_FOUND)
            
            if otp_code.otp != otp:
                return Response({"status": 400, "success": False, "message": "Invalid OTP"}, status=status.HTTP_400_BAD_REQUEST)
            if otp_code.is_expired():
                otp_code.delete()
                return Response({"status": 400, "success": False, "message": "OTP expired"}, status=status.HTTP_400_BAD_REQUEST)
            
            otp_code.delete()
            
            # Activate user upon successful OTP verification
            if not user.is_active:
                user.is_active = True
                user.save()
            
            return Response({
                "status": 200, "success": True, "message": "Otp verified successfully",
            }, status=status.HTTP_200_OK)
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)



class ResetPasswordView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = ResetPasswordSerializer

    @extend_schema(request=ResetPasswordSerializer)
    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            tokens = get_tokens_for_user(user)
            user_data = UserDataSerializer(user).data
            return Response({
                "status": 200, "success": True, "message": "Password reset successfully",
                "user": user_data, **tokens
            }, status=status.HTTP_200_OK)
        return Response({"status": 400, "success": False, "errors": format_serializer_errors(serializer.errors)}, status=status.HTTP_400_BAD_REQUEST)

class UploadDocumentView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = MultipleUploadDocumentSerializer

    @extend_schema(
        request=MultipleUploadDocumentSerializer,
        responses={
            200: OpenApiResponse(description="Documents uploaded successfully"),
            400: OpenApiResponse(description="Validation error / Mismatch error")
        }
    )
    def post(self, request):
        # Extract document types list
        if hasattr(request.data, 'getlist'):
            document_types = request.data.getlist('document_type')
        else:
            document_types = request.data.get('document_type')
            if not isinstance(document_types, list):
                document_types = [document_types] if document_types else []

        # Extract document files list
        if hasattr(request.FILES, 'getlist'):
            document_files = request.FILES.getlist('document_file') or request.FILES.getlist('file')
        else:
            document_files = request.FILES.get('document_file') or request.FILES.get('file')
            if not isinstance(document_files, list):
                document_files = [document_files] if document_files else []

        # Fallback to request.data if request.FILES didn't have it (parsed by DRF multipart parser into request.data)
        if not document_files:
            if hasattr(request.data, 'getlist'):
                document_files = request.data.getlist('document_file') or request.data.getlist('file')
            else:
                document_files = request.data.get('document_file') or request.data.get('file')
                if not isinstance(document_files, list):
                    document_files = [document_files] if document_files else []

        # Remove empty elements
        document_types = [t for t in document_types if t]
        document_files = [f for f in document_files if f]

        if not document_types or not document_files:
            return Response({
                "status": 400,
                "success": False,
                "errors": "Both document_type and document_file are required."
            }, status=status.HTTP_400_BAD_REQUEST)

        if len(document_types) != len(document_files):
            return Response({
                "status": 400,
                "success": False,
                "errors": f"Mismatch between document types ({len(document_types)}) and document files ({len(document_files)})."
            }, status=status.HTTP_400_BAD_REQUEST)

        created_docs = []
        for doc_type, doc_file in zip(document_types, document_files):
            doc = Document.objects.create(
                user=request.user,
                document_type=str(doc_type)[:20],
                document_file=doc_file
            )
            created_docs.append(doc)

        return Response({
            "status": 200,
            "success": True,
            "message": f"Successfully uploaded {len(created_docs)} document(s)."
        }, status=status.HTTP_200_OK)
