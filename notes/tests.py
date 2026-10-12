from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from .models import Note, Subject
from .validators import validate_pdf


class PdfValidatorTests(TestCase):
    def test_real_pdf_passes(self):
        pdf = SimpleUploadedFile('notes.pdf', b'%PDF-1.4 fake content')
        validate_pdf(pdf)  # should not raise

    def test_wrong_extension_fails(self):
        txt = SimpleUploadedFile('notes.txt', b'%PDF-1.4 fake content')
        with self.assertRaises(ValidationError):
            validate_pdf(txt)

    def test_too_big_file_fails(self):
        big = SimpleUploadedFile('big.pdf', b'%PDF-' + b'0' * (10 * 1024 * 1024))  # just over 10 MB
        with self.assertRaises(ValidationError):
            validate_pdf(big)

    def test_renamed_file_fails(self):
        # A PNG renamed to .pdf still has PNG bytes inside
        fake = SimpleUploadedFile('notes.pdf', b'\x89PNG\r\n\x1a\n')
        with self.assertRaises(ValidationError):
            validate_pdf(fake)


class ModelTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='pass12345')
        self.bob = User.objects.create_user('bob', password='pass12345')
        self.subject = Subject.objects.create(user=self.alice, name='Biology')

    def test_relationships(self):
        note = Note.objects.create(subject=self.subject, user=self.alice, title='Cells')
        # related_name lets us go "backwards" from subject/user to notes
        self.assertIn(note, self.subject.notes.all())
        self.assertIn(note, self.alice.notes.all())
        self.assertIn(self.subject, self.alice.subjects.all())

    def test_deleting_subject_deletes_notes(self):
        Note.objects.create(subject=self.subject, user=self.alice, title='Cells')
        self.subject.delete()
        self.assertEqual(Note.objects.count(), 0)

    def test_cannot_add_note_to_another_users_subject(self):
        note = Note(subject=self.subject, user=self.bob, title='Sneaky')
        with self.assertRaises(ValidationError):
            note.full_clean()

    def test_note_with_non_pdf_file_is_invalid(self):
        bad = SimpleUploadedFile('virus.pdf', b'MZ not a pdf')
        note = Note(subject=self.subject, user=self.alice, title='Bad', file=bad)
        with self.assertRaises(ValidationError):
            note.full_clean()


class DashboardTests(TestCase):
    def setUp(self):
        self.alice = User.objects.create_user('alice', password='pass12345')
        self.bob = User.objects.create_user('bob', password='pass12345')
        bio = Subject.objects.create(user=self.alice, name='Biology')
        Note.objects.create(subject=bio, user=self.alice, title='Cells')
        maths = Subject.objects.create(user=self.bob, name='Maths')
        Note.objects.create(subject=maths, user=self.bob, title='Algebra')

    def test_logged_out_user_is_redirected_to_login(self):
        response = self.client.get(reverse('dashboard'))
        # "next" remembers where they were going
        self.assertRedirects(response, f"{reverse('login')}?next={reverse('dashboard')}")

    def test_user_only_sees_own_data(self):
        self.client.login(username='alice', password='pass12345')
        response = self.client.get(reverse('dashboard'))
        self.assertContains(response, 'Biology')
        self.assertContains(response, 'Cells')
        self.assertNotContains(response, 'Maths')
        self.assertNotContains(response, 'Algebra')
