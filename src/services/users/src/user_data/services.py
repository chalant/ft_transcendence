from http import client
from urllib.parse import urlparse

from django.core.files.base import ContentFile

from user_data.models import UserProfile

PICTURE_HOST_SUFFIX = ".42.fr"


def create_profile(user, picture_url: str = "") -> UserProfile:
    """Create the profile of `user`, optionally downloading its picture.

    Only https pictures hosted under *.42.fr are fetched; anything else raises
    ValueError so a user-influenced URL can never make the server call an
    arbitrary host.
    """
    if not picture_url:
        return UserProfile.objects.create(user=user)

    parsed = urlparse(picture_url)
    host = parsed.hostname
    if parsed.scheme != "https" or not host or not host.endswith(PICTURE_HOST_SUFFIX):
        raise ValueError("Unsupported profile picture URL")

    connection = client.HTTPSConnection(host, timeout=5)
    try:
        connection.request("GET", parsed.path + ("?" + parsed.query if parsed.query else ""))
        response = connection.getresponse()
        if response.status != 200:
            raise ValueError(f"Profile picture download failed: {response.status}")
        body = response.read()
    finally:
        connection.close()

    image = ContentFile(body, name=f"{user.id}.jpg")
    return UserProfile.objects.create(user=user, profile_picture=image)
