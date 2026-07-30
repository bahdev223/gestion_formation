"""Tests for formations forms."""

from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image

from formations.forms import FormationForm


class FormationCoverFormTest(TestCase):
    def test_image_widget_accepte_les_formats_de_couverture(self):
        form = FormationForm()

        self.assertEqual(
            form.fields["image"].widget.attrs["accept"],
            "image/jpeg,image/png,image/webp",
        )
        self.assertEqual(form.fields["image"].label, "Image de couverture")

    def test_image_superieure_a_cinq_mo_est_refusee(self):
        image_buffer = BytesIO()
        Image.new("RGB", (2, 2), color="#15519a").save(
            image_buffer,
            format="PNG",
        )
        upload = SimpleUploadedFile(
            "couverture.png",
            image_buffer.getvalue() + b"0" * (5 * 1024 * 1024),
            content_type="image/png",
        )

        form = FormationForm()
        form.cleaned_data = {"image": upload}

        with self.assertRaisesMessage(
            ValidationError,
            "ne doit pas dépasser 5 Mo",
        ):
            form.clean_image()
