from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth import get_user_model
from organizations.models import Organization, OrganizationMembership, OrganizationRole

User = get_user_model()


class AuthenticationAPITests(APITestCase):
    def setUp(self):
        self.register_url = reverse('users:auth-register')
        self.login_url = reverse('users:auth-login')
        self.refresh_url = reverse('users:auth-token-refresh')
        self.logout_url = reverse('users:auth-logout')
        self.me_url = reverse('users:auth-me')
        self.change_password_url = reverse('users:auth-change-password')

        self.valid_email = "procurement@acme.com"
        self.valid_password = "SecurePassword123!"

    def test_user_registration_success(self):
        """Verify successful user registration provisions user, organization, and returns tokens."""
        payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
            "full_name": "Jane Doe",
            "organization_name": "Acme Procurement Corp",
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], self.valid_email)
        self.assertEqual(response.data['organization']['name'], "Acme Procurement Corp")
        self.assertEqual(response.data['organization']['role'], "owner")

        # Verify DB records
        user = User.objects.get(email=self.valid_email)
        self.assertEqual(user.full_name, "Jane Doe")
        membership = OrganizationMembership.objects.get(user=user)
        self.assertEqual(membership.role, OrganizationRole.OWNER)
        self.assertEqual(membership.organization.name, "Acme Procurement Corp")

    def test_registration_password_mismatch(self):
        """Verify registration fails if passwords do not match."""
        payload = {
            "email": "test@mismatch.com",
            "password": self.valid_password,
            "password_confirm": "DifferentPassword123!",
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('password_confirm', response.data)

    def test_registration_duplicate_email(self):
        """Verify registration rejects duplicate email addresses."""
        User.objects.create_user(email=self.valid_email, password=self.valid_password)
        payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
        }
        response = self.client.post(self.register_url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('email', response.data)

    def test_login_success(self):
        """Verify user can authenticate via email and receive JWT tokens with org context."""
        # Pre-register user with org
        reg_payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
            "full_name": "Jane Doe",
            "organization_name": "Acme Industries",
        }
        self.client.post(self.register_url, reg_payload, format='json')

        login_payload = {
            "email": self.valid_email,
            "password": self.valid_password,
        }
        response = self.client.post(self.login_url, login_payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('tokens', response.data)
        self.assertIn('access', response.data['tokens'])
        self.assertIn('refresh', response.data['tokens'])
        self.assertEqual(response.data['user']['email'], self.valid_email)
        self.assertEqual(len(response.data['user']['organizations']), 1)
        self.assertEqual(response.data['user']['organizations'][0]['name'], "Acme Industries")

    def test_login_invalid_credentials(self):
        """Verify login fails for wrong password."""
        User.objects.create_user(email=self.valid_email, password=self.valid_password)
        response = self.client.post(self.login_url, {"email": self.valid_email, "password": "WrongPassword!"}, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_token_refresh(self):
        """Verify token refresh endpoint issues a new access token."""
        reg_payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
        }
        reg_res = self.client.post(self.register_url, reg_payload, format='json')
        refresh_token = reg_res.data['tokens']['refresh']

        ref_res = self.client.post(self.refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(ref_res.status_code, status.HTTP_200_OK)
        self.assertIn('access', ref_res.data)

    def test_current_user_me_endpoint(self):
        """Verify /api/auth/me/ endpoint returns profile and supports partial updates."""
        reg_payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
            "full_name": "Original Name",
        }
        reg_res = self.client.post(self.register_url, reg_payload, format='json')
        access_token = reg_res.data['tokens']['access']

        # Unauthenticated access rejected
        unauth_res = self.client.get(self.me_url)
        self.assertEqual(unauth_res.status_code, status.HTTP_401_UNAUTHORIZED)

        # Authenticated access
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        res = self.client.get(self.me_url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['email'], self.valid_email)
        self.assertEqual(res.data['full_name'], "Original Name")

        # Update profile
        patch_res = self.client.patch(self.me_url, {"full_name": "Updated Name"}, format='json')
        self.assertEqual(patch_res.status_code, status.HTTP_200_OK)
        self.assertEqual(patch_res.data['full_name'], "Updated Name")

    def test_change_password(self):
        """Verify authenticated user can change password."""
        reg_payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
        }
        reg_res = self.client.post(self.register_url, reg_payload, format='json')
        access_token = reg_res.data['tokens']['access']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        new_password = "BrandNewSecurePassword456!"

        change_payload = {
            "old_password": self.valid_password,
            "new_password": new_password,
            "new_password_confirm": new_password,
        }
        res = self.client.post(self.change_password_url, change_payload, format='json')
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        # Clear credentials and verify login with new password
        self.client.credentials()
        login_res = self.client.post(self.login_url, {"email": self.valid_email, "password": new_password}, format='json')
        self.assertEqual(login_res.status_code, status.HTTP_200_OK)

    def test_logout_blacklists_token(self):
        """Verify logging out blacklists the refresh token."""
        reg_payload = {
            "email": self.valid_email,
            "password": self.valid_password,
            "password_confirm": self.valid_password,
        }
        reg_res = self.client.post(self.register_url, reg_payload, format='json')
        access_token = reg_res.data['tokens']['access']
        refresh_token = reg_res.data['tokens']['refresh']

        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {access_token}')
        logout_res = self.client.post(self.logout_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(logout_res.status_code, status.HTTP_200_OK)

        # Subsequent attempt to refresh with blacklisted token must fail with 401
        self.client.credentials()
        ref_res = self.client.post(self.refresh_url, {"refresh": refresh_token}, format='json')
        self.assertEqual(ref_res.status_code, status.HTTP_401_UNAUTHORIZED)
