from django.http import JsonResponse

def welcome_view(request):
    return JsonResponse({"message": "Welcome, user!"})
