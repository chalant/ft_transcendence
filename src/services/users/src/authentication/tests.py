from django.test import SimpleTestCase

from .validators import USERNAME_ERROR, validate_username


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
