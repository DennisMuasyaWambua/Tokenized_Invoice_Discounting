"""
File validators for invoice uploads.
"""
import os
import mimetypes
from django.core.exceptions import ValidationError
from django.conf import settings


class InvoiceFileValidator:
    """Validator for invoice file uploads (PDF and images)."""

    def __init__(self):
        self.config = getattr(settings, 'OCR_SETTINGS', {})
        self.supported_formats = self.config.get('SUPPORTED_FORMATS', ['pdf', 'jpg', 'jpeg', 'png'])
        self.max_file_size = self.config.get('MAX_FILE_SIZE', 10 * 1024 * 1024)  # 10MB default

    def validate_file_type(self, file):
        """
        Validate file type by extension and MIME type.

        Args:
            file: UploadedFile object

        Raises:
            ValidationError: If file type is not supported
        """
        # Get file extension
        file_name = file.name
        file_ext = os.path.splitext(file_name)[1].lower().lstrip('.')

        if file_ext not in self.supported_formats:
            raise ValidationError(
                f"Unsupported file format '.{file_ext}'. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )

        # Validate MIME type
        mime_type, _ = mimetypes.guess_type(file_name)
        valid_mime_types = {
            'pdf': 'application/pdf',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
        }

        expected_mime = valid_mime_types.get(file_ext)
        if mime_type and expected_mime and mime_type != expected_mime:
            raise ValidationError(
                f"File MIME type '{mime_type}' does not match extension '.{file_ext}'"
            )

    def validate_file_size(self, file):
        """
        Validate file size.

        Args:
            file: UploadedFile object

        Raises:
            ValidationError: If file size exceeds maximum
        """
        if file.size > self.max_file_size:
            max_size_mb = self.max_file_size / (1024 * 1024)
            actual_size_mb = file.size / (1024 * 1024)
            raise ValidationError(
                f"File size ({actual_size_mb:.2f} MB) exceeds maximum allowed size ({max_size_mb:.1f} MB)"
            )

    def validate_file_content(self, file):
        """
        Basic file integrity check.

        Args:
            file: UploadedFile object

        Raises:
            ValidationError: If file appears corrupted
        """
        # Check if file is empty
        if file.size == 0:
            raise ValidationError("File is empty")

        # Try to read first few bytes to ensure file is readable
        try:
            file.seek(0)
            first_bytes = file.read(1024)
            file.seek(0)  # Reset file pointer

            if not first_bytes:
                raise ValidationError("File is empty or unreadable")

            # Basic magic number checks for file types
            file_ext = os.path.splitext(file.name)[1].lower().lstrip('.')

            if file_ext == 'pdf':
                # PDF files start with %PDF
                if not first_bytes.startswith(b'%PDF'):
                    raise ValidationError("File does not appear to be a valid PDF")

            elif file_ext in ['jpg', 'jpeg']:
                # JPEG files start with FF D8 FF
                if not first_bytes.startswith(b'\xff\xd8\xff'):
                    raise ValidationError("File does not appear to be a valid JPEG image")

            elif file_ext == 'png':
                # PNG files start with 89 50 4E 47
                if not first_bytes.startswith(b'\x89PNG'):
                    raise ValidationError("File does not appear to be a valid PNG image")

        except Exception as e:
            raise ValidationError(f"File validation failed: {str(e)}")

    def validate(self, file):
        """
        Run all validations on the file.

        Args:
            file: UploadedFile object

        Raises:
            ValidationError: If any validation fails
        """
        self.validate_file_type(file)
        self.validate_file_size(file)
        self.validate_file_content(file)

    def __call__(self, file):
        """Allow validator to be called directly."""
        self.validate(file)
