from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class SignUpTests(TestCase):
    def test_signup_page_loads(self):
        response = self.client.get(reverse('signup'))
        self.assertEqual(response.status_code, 200)

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(reverse('signup'), {
            'username': 'alice',
            'email': 'alice@example.com',
            'password1': 'a-Strong-pass-123',
            'password2': 'a-Strong-pass-123',
        })
        self.assertRedirects(response, reverse('dashboard'))
        self.assertTrue(User.objects.filter(username='alice').exists())
        # The user should now be logged in
        self.assertTrue(self.client.get(reverse('dashboard')).context['user'].is_authenticated)

    def test_signup_requires_email(self):
        response = self.client.post(reverse('signup'), {
            'username': 'alice',
            'password1': 'a-Strong-pass-123',
            'password2': 'a-Strong-pass-123',
        })
        self.assertEqual(response.status_code, 200)  # form shown again with errors
        self.assertFalse(User.objects.exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        User.objects.create_user('alice', password='a-Strong-pass-123')

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(reverse('login'), {
            'username': 'alice', 'password': 'a-Strong-pass-123',
        })
        self.assertRedirects(response, reverse('dashboard'))

    def test_wrong_password_shows_error(self):
        response = self.client.post(reverse('login'), {'username': 'alice', 'password': 'wrong'})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Please enter a correct username and password')

    def test_logout_logs_user_out(self):
        self.client.login(username='alice', password='a-Strong-pass-123')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))
        # Dashboard is protected again
        self.assertEqual(self.client.get(reverse('dashboard')).status_code, 302)


class NavbarTests(TestCase):
    def test_logged_out_navbar(self):
        response = self.client.get(reverse('login'))
        self.assertContains(response, 'Sign up')
        self.assertNotContains(response, 'Log out')

    def test_logged_in_navbar(self):
        User.objects.create_user('alice', password='a-Strong-pass-123')
        self.client.login(username='alice', password='a-Strong-pass-123')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Log out')
        self.assertContains(response, '<i class="bi bi-person-circle me-1"></i>alice')
        self.assertNotContains(response, 'Sign up')
