from unittest.mock import patch

import pytest
from django.urls import reverse

from trade_portal.documents.models import Document, DocumentFile


@pytest.mark.django_db
def test_document_issue(normal_user, ftas):
    assert Document.objects.count() == 0
    nr = normal_user.web_client.get(reverse('documents:list'))
    assert nr.status_code == 200

    nr = normal_user.web_client.get(reverse('documents:create', args={"dtype": "non_pref_coo"}))

    # is it valid redirect?
    assert nr.status_code == 302
    assert nr.url.startswith("/documents/create-dtype/")
    assert len(nr.url) == len("/documents/create-dtype/fee3b66f-8276-4348-b145-40c627c1154d/")

    create_url = nr.url

    nr = normal_user.web_client.get(create_url)
    assert nr.status_code == 200
    assert nr.context.get("form").__class__.__name__ == "DocumentCreateForm"

    with open('/app/trade_portal/documents/tests/assets/A5.pdf', 'rb') as fp:
        nr = normal_user.web_client.post(
            create_url,
            {'file': fp}
        )

    assert nr.status_code == 302
    assert nr.url.endswith("/fill/")
    assert len(nr.url) == len("/documents/c617c471-06b2-41a8-94ff-7994a8ea11f9/fill/")

    fill_url = nr.url
    nr = normal_user.web_client.get(fill_url)
    assert nr.status_code == 200
    assert nr.context.get("form").__class__.__name__ == "DraftDocumentUpdateForm"

    assert Document.objects.count() == 1
    assert DocumentFile.objects.count() == 1

    doc = Document.objects.first()

    df = DocumentFile.objects.first()
    assert df.is_watermarked is False
    assert df.size == 7379  # bytes, test PDF size

    nr = normal_user.web_client.post(
        fill_url,
        {
            'document_number': "TestDocument123",
            'importing_country': "SG",
            'exporter': "51 824 753 556",
            'importer_name': "",
            'consignment_ref_doc_number': "",
        }
    )
    assert nr.status_code == 302, nr.context["form"].errors
    assert nr.url.endswith("/issue/")

    issue_url = nr.url

    nr = normal_user.web_client.get(issue_url)
    assert nr.status_code == 200
    assert nr.context["IS_PDF_ENCRYPTED"] is False
    assert nr.context["IS_PDF_UNPARSEABLE"] is False
    assert nr.context["SHOW_QR_CODE_ATTACHMENT"] is True
    assert not nr.context["data_warnings"]

    with patch('trade_portal.documents.tasks.lodge_document.apply_async') as mock_task:
        nr = normal_user.web_client.post(
            issue_url,
            {
                'issue': "Issue",
                'qr_x': "50",
                'qr_y': "50",
            }
        )
        assert nr.status_code == 302
        assert nr.url == reverse("documents:detail", kwargs={"pk": doc.pk})
        assert mock_task.call_count == 1