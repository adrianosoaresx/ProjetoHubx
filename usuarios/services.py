from django.shortcuts import render
from django.contrib.auth import get_user_model
def create_user(username, email, password, first_name='', last_name=''):
    """Create a new user if the username does not exist."""
    User = get_user_model()
    if User.objects.filter(username=username).exists():
        return None
    user = User.objects.create_user(
        username=username,
        email=email,
        password=password,
        first_name=first_name,
        last_name=last_name,
    )
    return user
