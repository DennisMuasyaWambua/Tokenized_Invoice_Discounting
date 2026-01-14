"""
OCR extraction utilities for invoice processing.
Handles PDF and image files using pytesseract.
"""
import os
import logging
from typing import Dict, List, Optional
from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
from pdf2image import convert_from_path
from django.conf import settings

logger = logging.getLogger('discounting.ocr')


class ImageConverter:
    """Converts PDF files to images for OCR processing."""

    @staticmethod
    def pdf_to_images(pdf_path: str) -> List[Image.Image]:
        """
        Convert PDF file to list of PIL Image objects.

        Args:
            pdf_path: Path to PDF file

        Returns:
            List of PIL Image objects, one per page

        Raises:
            Exception: If PDF conversion fails
        """
        try:
            images = convert_from_path(
                pdf_path,
                dpi=300,  # High DPI for better OCR accuracy
                fmt='jpeg'
            )
            logger.info(f"Converted PDF to {len(images)} images")
            return images
        except Exception as e:
            logger.error(f"PDF conversion failed: {str(e)}")
            raise Exception(f"Failed to convert PDF: {str(e)}")

    @staticmethod
    def load_image(image_path: str) -> Image.Image:
        """
        Load image file as PIL Image.

        Args:
            image_path: Path to image file

        Returns:
            PIL Image object

        Raises:
            Exception: If image loading fails
        """
        try:
            image = Image.open(image_path)
            logger.info(f"Loaded image: {image.format}, {image.size}")
            return image
        except Exception as e:
            logger.error(f"Image loading failed: {str(e)}")
            raise Exception(f"Failed to load image: {str(e)}")


class OCREngine:
    """Wrapper for pytesseract OCR engine with preprocessing."""

    def __init__(self):
        self.config = getattr(settings, 'OCR_SETTINGS', {})
        self.tesseract_config = self.config.get('TESSERACT_CONFIG', '--oem 3 --psm 6')
        self.lang = self.config.get('TESSERACT_LANG', 'eng')

    def preprocess_image(self, image: Image.Image) -> Image.Image:
        """
        Preprocess image for better OCR accuracy.

        Args:
            image: PIL Image object

        Returns:
            Preprocessed PIL Image object
        """
        # Convert to grayscale
        if image.mode != 'L':
            image = image.convert('L')

        # Enhance contrast
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.0)

        # Apply slight sharpening
        image = image.filter(ImageFilter.SHARPEN)

        # Resize if too small (improves OCR for small text)
        width, height = image.size
        if width < 1000 or height < 1000:
            scale_factor = max(1000 / width, 1000 / height)
            new_size = (int(width * scale_factor), int(height * scale_factor))
            image = image.resize(new_size, Image.LANCZOS)

        return image

    def extract_text(self, image: Image.Image) -> Dict:
        """
        Extract text from image using pytesseract.

        Args:
            image: PIL Image object

        Returns:
            Dict with 'text' and 'confidence' keys
        """
        try:
            # Preprocess image
            processed_image = self.preprocess_image(image)

            # Extract text
            text = pytesseract.image_to_string(
                processed_image,
                lang=self.lang,
                config=self.tesseract_config
            )

            # Get confidence score
            data = pytesseract.image_to_data(
                processed_image,
                lang=self.lang,
                config=self.tesseract_config,
                output_type=pytesseract.Output.DICT
            )

            # Calculate average confidence
            confidences = [int(conf) for conf in data['conf'] if conf != '-1']
            avg_confidence = sum(confidences) / len(confidences) if confidences else 0

            return {
                'text': text.strip(),
                'confidence': avg_confidence / 100.0  # Normalize to 0-1
            }
        except Exception as e:
            logger.error(f"Text extraction failed: {str(e)}")
            return {
                'text': '',
                'confidence': 0.0,
                'error': str(e)
            }


class OCRExtractor:
    """Main OCR extraction orchestrator."""

    def __init__(self):
        self.converter = ImageConverter()
        self.ocr_engine = OCREngine()
        self.config = getattr(settings, 'OCR_SETTINGS', {})

    def validate_file(self, file_path: str) -> Dict:
        """
        Validate file exists and has correct format.

        Args:
            file_path: Path to file

        Returns:
            Dict with 'valid' boolean and optional 'error' message
        """
        if not os.path.exists(file_path):
            return {'valid': False, 'error': 'File does not exist'}

        file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')
        supported_formats = self.config.get('SUPPORTED_FORMATS', ['pdf', 'jpg', 'jpeg', 'png'])

        if file_ext not in supported_formats:
            return {
                'valid': False,
                'error': f'Unsupported format. Supported formats: {", ".join(supported_formats)}'
            }

        file_size = os.path.getsize(file_path)
        max_size = self.config.get('MAX_FILE_SIZE', 10 * 1024 * 1024)

        if file_size > max_size:
            return {
                'valid': False,
                'error': f'File size exceeds maximum allowed size ({max_size / (1024 * 1024):.1f} MB)'
            }

        return {'valid': True}

    def extract_text(self, file_path: str) -> Dict:
        """
        Extract text from file (PDF or image).

        Args:
            file_path: Path to file

        Returns:
            Dict containing:
                - success: Boolean
                - text: Extracted text (if successful)
                - confidence: Average confidence score
                - pages: Number of pages processed
                - errors: List of errors (if any)
        """
        result = {
            'success': False,
            'text': '',
            'confidence': 0.0,
            'pages': 0,
            'errors': []
        }

        # Validate file
        validation = self.validate_file(file_path)
        if not validation['valid']:
            result['errors'].append(validation['error'])
            return result

        try:
            file_ext = os.path.splitext(file_path)[1].lower().lstrip('.')

            # Convert to images
            if file_ext == 'pdf':
                images = self.converter.pdf_to_images(file_path)
            else:
                images = [self.converter.load_image(file_path)]

            result['pages'] = len(images)

            # Extract text from all images/pages
            all_text = []
            all_confidences = []

            for i, image in enumerate(images, 1):
                logger.info(f"Processing page/image {i}/{len(images)}")
                ocr_result = self.ocr_engine.extract_text(image)

                if 'error' in ocr_result:
                    result['errors'].append(f"Page {i}: {ocr_result['error']}")
                    continue

                all_text.append(ocr_result['text'])
                all_confidences.append(ocr_result['confidence'])

            # Combine results
            if all_text:
                result['text'] = '\n\n'.join(all_text)
                result['confidence'] = sum(all_confidences) / len(all_confidences)
                result['success'] = True
                logger.info(f"OCR completed: {len(all_text)} pages, avg confidence: {result['confidence']:.2f}")
            else:
                result['errors'].append('No text could be extracted')
                logger.warning("OCR completed but no text extracted")

        except Exception as e:
            error_msg = f"OCR extraction failed: {str(e)}"
            result['errors'].append(error_msg)
            logger.error(error_msg)

        return result
