import os
import shutil
import tempfile

from django.contrib.auth.models import User
from django.contrib.messages import get_messages
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import Note, Subject

# Uploaded files go to a temporary folder instead of the real media/ folder
TEST_MEDIA = tempfile.mkdtemp()


def make_pdf(name='notes.pdf'):
    return SimpleUploadedFile(name, b'%PDF-1.4 test file', content_type='application/pdf')


def message_texts(response):
    return [str(m) for m in get_messages(response.wsgi_request)]


@override_settings(MEDIA_ROOT=TEST_MEDIA)
class BaseTestCase(TestCase):
    """Two users, each with one subject and one note. Alice is logged in."""

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(TEST_MEDIA, ignore_errors=True)
        super().tearDownClass()

    def setUp(self):
        self.alice = User.objects.create_user('alice', password='pass12345')
        self.bob = User.objects.create_user('bob', password='pass12345')
        self.alice_subject = Subject.objects.create(user=self.alice, name='Biology')
        self.alice_note = Note.objects.create(subject=self.alice_subject, user=self.alice, title='Cells')
        self.bob_subject = Subject.objects.create(user=self.bob, name='Maths')
        self.bob_note = Note.objects.create(subject=self.bob_subject, user=self.bob, title='Algebra')
        self.client.login(username='alice', password='pass12345')


class LoginRequiredTests(BaseTestCase):
    def test_every_page_redirects_logged_out_users(self):
        self.client.logout()
        urls = [
            reverse('subject_list'), reverse('subject_create'),
            reverse('subject_detail', args=[self.alice_subject.pk]),
            reverse('subject_update', args=[self.alice_subject.pk]),
            reverse('subject_delete', args=[self.alice_subject.pk]),
            reverse('note_list'), reverse('note_create'),
            reverse('note_detail', args=[self.alice_note.pk]),
            reverse('note_update', args=[self.alice_note.pk]),
            reverse('note_delete', args=[self.alice_note.pk]),
            reverse('note_file', args=[self.alice_note.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 302)
                self.assertTrue(response.url.startswith(reverse('login')))


class OwnershipTests(BaseTestCase):
    def test_other_users_objects_return_404(self):
        urls = [
            reverse('subject_detail', args=[self.bob_subject.pk]),
            reverse('subject_update', args=[self.bob_subject.pk]),
            reverse('subject_delete', args=[self.bob_subject.pk]),
            reverse('note_detail', args=[self.bob_note.pk]),
            reverse('note_update', args=[self.bob_note.pk]),
            reverse('note_delete', args=[self.bob_note.pk]),
            reverse('note_file', args=[self.bob_note.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_cannot_delete_or_edit_other_users_objects_with_post(self):
        self.client.post(reverse('note_delete', args=[self.bob_note.pk]))
        self.client.post(reverse('subject_delete', args=[self.bob_subject.pk]))
        self.client.post(reverse('note_update', args=[self.bob_note.pk]),
                         {'subject': self.bob_subject.pk, 'title': 'Hacked'})
        self.bob_note.refresh_from_db()
        self.assertEqual(self.bob_note.title, 'Algebra')
        self.assertTrue(Subject.objects.filter(pk=self.bob_subject.pk).exists())

    def test_lists_only_show_own_objects(self):
        subjects = self.client.get(reverse('subject_list'))
        self.assertContains(subjects, 'Biology')
        self.assertNotContains(subjects, 'Maths')
        notes = self.client.get(reverse('note_list'))
        self.assertContains(notes, 'Cells')
        self.assertNotContains(notes, 'Algebra')

    def test_cannot_put_note_in_other_users_subject(self):
        response = self.client.post(reverse('note_create'),
                                    {'subject': self.bob_subject.pk, 'title': 'Sneaky'})
        self.assertEqual(response.status_code, 200)  # form re-shown with an error
        self.assertFalse(Note.objects.filter(title='Sneaky').exists())

    def test_subject_dropdown_only_has_own_subjects(self):
        response = self.client.get(reverse('note_create'))
        self.assertContains(response, 'Biology')
        self.assertNotContains(response, 'Maths')


class SubjectCrudTests(BaseTestCase):
    def test_create(self):
        response = self.client.post(reverse('subject_create'), {'name': 'History', 'description': ''})
        subject = Subject.objects.get(name='History')
        self.assertEqual(subject.user, self.alice)  # owner set automatically
        self.assertRedirects(response, subject.get_absolute_url())
        self.assertIn('Subject "History" was created.', message_texts(response))

    def test_duplicate_name_shows_error(self):
        response = self.client.post(reverse('subject_create'), {'name': 'biology'})
        self.assertContains(response, 'You already have a subject with this name.')

    def test_same_name_as_another_user_is_fine(self):
        self.client.post(reverse('subject_create'), {'name': 'Maths'})
        self.assertTrue(Subject.objects.filter(user=self.alice, name='Maths').exists())

    def test_update(self):
        response = self.client.post(reverse('subject_update', args=[self.alice_subject.pk]),
                                    {'name': 'Biology 101', 'description': 'Year 1'})
        self.alice_subject.refresh_from_db()
        self.assertEqual(self.alice_subject.name, 'Biology 101')
        self.assertIn('Subject "Biology 101" was updated.', message_texts(response))

    def test_delete_warns_then_removes_subject_and_notes(self):
        page = self.client.get(reverse('subject_delete', args=[self.alice_subject.pk]))
        self.assertContains(page, 'Its 1 note(s) and their PDFs will be deleted too.')
        response = self.client.post(reverse('subject_delete', args=[self.alice_subject.pk]))
        self.assertRedirects(response, reverse('subject_list'))
        self.assertFalse(Note.objects.filter(pk=self.alice_note.pk).exists())
        self.assertIn('"Biology" was deleted.', message_texts(response))


class NoteCrudTests(BaseTestCase):
    def test_create_with_pdf(self):
        response = self.client.post(reverse('note_create'), {
            'subject': self.alice_subject.pk, 'title': 'Mitosis',
            'content': 'Cell division', 'file': make_pdf(),
        })
        note = Note.objects.get(title='Mitosis')
        self.assertEqual(note.user, self.alice)
        self.assertTrue(note.file.name.endswith('.pdf'))
        self.assertRedirects(response, note.get_absolute_url())
        self.assertIn('Note "Mitosis" was created.', message_texts(response))

    def test_non_pdf_upload_is_rejected(self):
        fake = SimpleUploadedFile('virus.pdf', b'MZ not a pdf')
        response = self.client.post(reverse('note_create'), {
            'subject': self.alice_subject.pk, 'title': 'Bad', 'file': fake,
        })
        self.assertContains(response, 'This file is not a valid PDF.')
        self.assertFalse(Note.objects.filter(title='Bad').exists())

    def test_subject_preselected_from_url(self):
        response = self.client.get(reverse('note_create') + f'?subject={self.alice_subject.pk}')
        self.assertContains(response, f'<option value="{self.alice_subject.pk}" selected>')

    def test_create_without_subjects_redirects(self):
        Subject.objects.filter(user=self.alice).delete()
        response = self.client.get(reverse('note_create'))
        self.assertRedirects(response, reverse('subject_create'))

    def test_update(self):
        response = self.client.post(reverse('note_update', args=[self.alice_note.pk]), {
            'subject': self.alice_subject.pk, 'title': 'Cell biology', 'content': 'Updated',
        })
        self.alice_note.refresh_from_db()
        self.assertEqual(self.alice_note.title, 'Cell biology')
        self.assertIn('Note "Cell biology" was updated.', message_texts(response))

    def test_delete(self):
        response = self.client.post(reverse('note_delete', args=[self.alice_note.pk]))
        self.assertRedirects(response, reverse('note_list'))
        self.assertFalse(Note.objects.filter(pk=self.alice_note.pk).exists())
        self.assertIn('"Cells" was deleted.', message_texts(response))

    def test_filter_by_subject(self):
        other = Subject.objects.create(user=self.alice, name='Chemistry')
        Note.objects.create(subject=other, user=self.alice, title='Atoms')
        response = self.client.get(reverse('note_list') + f'?subject={other.pk}')
        self.assertContains(response, 'Atoms')
        self.assertNotContains(response, 'Cells')


class PdfFileTests(BaseTestCase):
    def upload(self, note, pdf):
        note.file = pdf
        note.save()
        return note.file.path

    def test_owner_can_view_pdf(self):
        self.upload(self.alice_note, make_pdf())
        response = self.client.get(reverse('note_file', args=[self.alice_note.pk]))
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'application/pdf')
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-1.4 test file')

    def test_note_without_pdf_returns_404(self):
        self.assertEqual(self.client.get(reverse('note_file', args=[self.alice_note.pk])).status_code, 404)

    def test_deleting_note_deletes_file(self):
        path = self.upload(self.alice_note, make_pdf())
        self.client.post(reverse('note_delete', args=[self.alice_note.pk]))
        self.assertFalse(os.path.exists(path))

    def test_replacing_file_deletes_old_one(self):
        old_path = self.upload(self.alice_note, make_pdf('old.pdf'))
        self.client.post(reverse('note_update', args=[self.alice_note.pk]), {
            'subject': self.alice_subject.pk, 'title': 'Cells', 'file': make_pdf('new.pdf'),
        })
        self.alice_note.refresh_from_db()
        self.assertIn('new', self.alice_note.file.name)
        self.assertFalse(os.path.exists(old_path))

    def test_remove_file_checkbox(self):
        path = self.upload(self.alice_note, make_pdf())
        self.client.post(reverse('note_update', args=[self.alice_note.pk]), {
            'subject': self.alice_subject.pk, 'title': 'Cells', 'remove_file': 'on',
        })
        self.alice_note.refresh_from_db()
        self.assertFalse(self.alice_note.file)
        self.assertFalse(os.path.exists(path))


class DashboardStatsTests(BaseTestCase):
    def test_counts_only_own_data(self):
        response = self.client.get(reverse('dashboard'))
        self.assertEqual(response.context['subject_count'], 1)
        self.assertEqual(response.context['note_count'], 1)
        self.assertEqual(list(response.context['recent_notes']), [self.alice_note])


class PagesRenderTests(BaseTestCase):
    def test_every_page_loads_for_owner(self):
        self.alice_note.file = make_pdf()
        self.alice_note.save()
        urls = [
            reverse('dashboard'),
            reverse('subject_list'), reverse('subject_create'),
            reverse('subject_detail', args=[self.alice_subject.pk]),
            reverse('subject_update', args=[self.alice_subject.pk]),
            reverse('subject_delete', args=[self.alice_subject.pk]),
            reverse('note_list'), reverse('note_create'),
            reverse('note_detail', args=[self.alice_note.pk]),
            reverse('note_update', args=[self.alice_note.pk]),
            reverse('note_delete', args=[self.alice_note.pk]),
        ]
        for url in urls:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 200)

    def test_pagination_keeps_subject_filter(self):
        for i in range(12):
            Note.objects.create(subject=self.alice_subject, user=self.alice, title=f'Note {i}')
        response = self.client.get(reverse('note_list') + f'?subject={self.alice_subject.pk}')
        self.assertContains(response, f'?subject={self.alice_subject.pk}&amp;page=2')


class SearchTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.chem = Subject.objects.create(user=self.alice, name='Chemistry')
        Note.objects.create(subject=self.alice_subject, user=self.alice, title='Mitosis',
                            content='How cells divide')
        Note.objects.create(subject=self.chem, user=self.alice, title='Atoms',
                            content='Protons and neutrons')
        # Bob's note also mentions cells, but Alice must never see it
        Note.objects.create(subject=self.bob_subject, user=self.bob, title='Cell counting',
                            content='cells cells')

    def search(self, **params):
        response = self.client.get(reverse('note_list'), params)
        return [note.title for note in response.context['note_list']]

    def test_matches_title(self):
        self.assertEqual(self.search(q='atoms'), ['Atoms'])  # case-insensitive

    def test_matches_content(self):
        self.assertEqual(self.search(q='neutrons'), ['Atoms'])

    def test_matches_title_or_content(self):
        # "Cells" title + "How cells divide" content; Bob's note excluded
        self.assertCountEqual(self.search(q='cell'), ['Cells', 'Mitosis'])

    def test_search_combined_with_subject_filter(self):
        self.assertEqual(self.search(q='cell', subject=self.chem.pk), [])
        self.assertCountEqual(self.search(q='cell', subject=self.alice_subject.pk), ['Cells', 'Mitosis'])

    def test_no_results_message(self):
        response = self.client.get(reverse('note_list'), {'q': 'quantum'})
        self.assertContains(response, 'No notes match your search.')
        self.assertContains(response, '0 notes found')

    def test_blank_search_shows_everything(self):
        self.assertEqual(len(self.search(q='   ')), 3)

    def test_ten_per_page_and_search_kept_in_page_links(self):
        for i in range(15):
            Note.objects.create(subject=self.alice_subject, user=self.alice, title=f'Revision {i}')
        response = self.client.get(reverse('note_list'), {'q': 'revision'})
        self.assertEqual(len(response.context['note_list']), 10)
        self.assertContains(response, '?q=revision&amp;page=2')
