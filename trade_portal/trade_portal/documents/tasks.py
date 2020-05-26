import logging

from trade_portal.documents.models import (
    Document,
)
from trade_portal.documents.services import DocumentService, NodeService
from config import celery_app

logger = logging.getLogger(__name__)


# @app.task
# def notify_about_certificate_created(certificate_id):
#     c = Document.objects.get(pk=certificate_id)
#     send_mail(
#         'Certificate application has been approved',
#         """Just letting you know that your certificate {} has been lodged""".format(
#             c
#         ),
#         settings.DEFAULT_FROM_EMAIL,
#         [c.created_by.email],
#         fail_silently=False,
#     )


@celery_app.task(ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def lodge_document(document_id=None):
    DocumentService().lodge(
        Document.objects.get(pk=document_id)
    )
    return


@celery_app.task(bind=True, ignore_result=True,
                 max_retries=3, interval_start=10, interval_step=10, interval_max=50)
def update_message_by_sender_ref(self, sender_ref):
    NodeService().update_message_by_sender_ref(sender_ref)