from django.contrib.auth import authenticate, login, logout, get_user_model
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.middleware.csrf import get_token
from django.shortcuts import render
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.conf import settings
from django.core.files.storage import FileSystemStorage
import json

CustomUser = get_user_model()


@csrf_exempt
def register_view(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    # prefer email but accept username for compatibility
    email = (data.get('email') or data.get('username'))
    password = data.get('password')

    if not email or not password:
        return JsonResponse({"error": "Email and password required"}, status=400)

    # validate email format
    try:
        validate_email(email)
    except ValidationError:
        return JsonResponse({"error": "Invalid email address"}, status=400)

    username = email

    if CustomUser.objects.filter(username=username).exists():
        return JsonResponse({"error": "Email already registered"}, status=400)

    user = CustomUser.objects.create_user(username=username, email=email, password=password)
    login(request, user)
    return JsonResponse({"success": True, "username": user.username})


@csrf_exempt
def login_view(request):
    if request.method != 'POST':
        return JsonResponse({"error": "POST required"}, status=400)

    try:
        data = json.loads(request.body)
    except Exception:
        return JsonResponse({"error": "Invalid JSON"}, status=400)

    identifier = data.get('email') or data.get('username')
    password = data.get('password')

    if not identifier or not password:
        return JsonResponse({"error": "Email/username and password required"}, status=400)

    user = authenticate(request, username=identifier, password=password)
    if user:
        login(request, user)
        return JsonResponse({"success": True, "username": user.username})

    return JsonResponse({"error": "Invalid credentials"}, status=400)


def get_csrf(request):
    return JsonResponse({'csrfToken': get_token(request)})


def chat_room(request):
    return render(request, 'chat/room.html')


def current_user(request):
    user = getattr(request, 'user', None)
    if user and user.is_authenticated:
        return JsonResponse({'username': user.username})
    return JsonResponse({'error': 'unauthorized'}, status=401)


@csrf_exempt
def logout_view(request):
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    try:
        logout(request)
        return JsonResponse({'success': True})
    except Exception:
        return JsonResponse({'error': 'logout failed'}, status=500)


@csrf_exempt
def upload_image(request):
    """Accepts a multipart POST with an 'image' file, saves it to MEDIA_ROOT and returns its absolute URL.

    Requires the user to be authenticated (returns 401 otherwise).
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)

    user = getattr(request, 'user', None)
    if not (user and user.is_authenticated):
        return JsonResponse({'error': 'unauthorized'}, status=401)

    if 'image' not in request.FILES:
        return JsonResponse({'error': 'image file required'}, status=400)

    image = request.FILES['image']
    fs = FileSystemStorage(location=str(settings.MEDIA_ROOT))
    filename = fs.save(image.name, image)
    rel_url = settings.MEDIA_URL + filename
    abs_url = request.build_absolute_uri(rel_url)
    return JsonResponse({'image_url': abs_url})