from django.core.exceptions import ValidationError

MAX_PDF_SIZE_MB = 10


def validate_pdf(file):
    """Make sure an uploaded file is really a PDF, and not too big."""
    # 1. Check the size first (file.size is in bytes)
    if file.size > MAX_PDF_SIZE_MB * 1024 * 1024:
        raise ValidationError(f'PDFs can be at most {MAX_PDF_SIZE_MB} MB.')

    # 2. Check the file extension
    if not file.name.lower().endswith('.pdf'):
        raise ValidationError('Only PDF files are allowed.')

    # 3. Check the file contents. Every real PDF starts with "%PDF-",
    #    so a renamed .exe or .jpg will fail here.
    file.seek(0)
    header = file.read(5)
    file.seek(0)  # rewind so Django can save the whole file afterwards
    if header != b'%PDF-':
        raise ValidationError('This file is not a valid PDF.')
