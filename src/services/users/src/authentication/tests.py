import time

import jwt
from django.contrib.auth import get_user_model
from django.test import RequestFactory, SimpleTestCase, TestCase

from . import tokens
from .models import UserToken
from .validators import USERNAME_ERROR, validate_username
from .views import check_jwt


class ValidateUsernameTests(SimpleTestCase):
    def test_accepts_allowed_characters(self):
        self.assertIsNone(validate_username("alice_01"))
        self.assertIsNone(validate_username("a-b_C"))
        self.assertIsNone(validate_username("x" * 25))

    def test_rejects_html(self):
        self.assertEqual(validate_username("<svg onload=alert(1)>"), USERNAME_ERROR)

    def test_rejects_bad_length(self):
        self.assertEqual(validate_username("abcd"), USERNAME_ERROR)
        self.assertEqual(validate_username("x" * 26), USERNAME_ERROR)

    def test_rejects_trailing_newline(self):
        self.assertEqual(validate_username("alice_01\n"), USERNAME_ERROR)

    def test_rejects_non_string(self):
        self.assertEqual(validate_username(None), USERNAME_ERROR)


class TokenTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("alice_01", password="secret1")

    def _request(self, token):
        return RequestFactory().get("/", HTTP_AUTHORIZATION=f"Bearer {token}")

    def test_roundtrip_carries_user_id(self):
        payload = tokens.verify(tokens.issue(self.user))
        self.assertEqual(payload["sub"], str(self.user.id))

    def test_tampered_signature_is_rejected(self):
        token = tokens.issue(self.user)
        forged = token[:-2] + ("AA" if not token.endswith("AA") else "BB")
        self.assertIsNone(tokens.verify(forged))

    def test_token_signed_with_other_key_is_rejected(self):
        forged = jwt.encode(
            {"sub": str(self.user.id), "exp": int(time.time()) + 60, "iss": tokens.ISSUER},
            "not-the-secret", algorithm="HS256")
        self.assertIsNone(tokens.verify(forged))

    def test_expired_token_is_rejected(self):
        expired = jwt.encode(
            {"sub": str(self.user.id), "exp": int(time.time()) - 10, "iss": tokens.ISSUER},
            tokens.SECRET, algorithm="HS256")
        self.assertIsNone(tokens.verify(expired))

    def test_check_jwt_accepts_stored_token(self):
        token = tokens.issue(self.user)
        UserToken.objects.create(user=self.user, token=token)
        self.assertEqual(check_jwt(self._request(token)), self.user)

    def test_check_jwt_rejects_token_after_logout(self):
        token = tokens.issue(self.user)
        UserToken.objects.create(user=self.user, token=token).delete()
        self.assertIsNone(check_jwt(self._request(token)))

    def test_check_jwt_rejects_and_drops_token_of_another_user(self):
        other = get_user_model().objects.create_user("bob_0001", password="secret1")
        token = tokens.issue(other)
        UserToken.objects.create(user=self.user, token=token)
        self.assertIsNone(check_jwt(self._request(token)))
        self.assertFalse(UserToken.objects.filter(token=token).exists())
