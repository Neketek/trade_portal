import base64
import json
import logging
import urllib

import requests

from constance import config
from django.contrib import messages
from django.views.generic import TemplateView
from django.utils.html import escape

from trade_portal.documents.services.lodge import AESCipher

logger = logging.getLogger(__name__)


class OaVerificationError(Exception):
    pass


class OaVerificationView(TemplateView):
    template_name = "oa_verify/verification.html"

    def dispatch(self, request, *args, **kwargs):
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, *args, **kwargs):
        c = super().get_context_data(*args, **kwargs)
        if self.request.POST:
            c["verification_result"] = self.perform_verification()
        return c

    def post(self, request, *args, **kwargs):
        # get_context_data calls the verification step
        return super().get(request, *args, **kwargs)

    def perform_verification(self):
        """
        Return dict of the next format:
        {
            "status": "valid|invalid|error",

            # only if valid
            "attachments": [list of attachments to that OA doc to display them to user]
            "rendered": "<html>...</html"> - something which is rendered using rendererer from the doc...
            "unwrapped_file": {...},

            # always present
            "verify_result": [list of dicts describing verification aspects]
            "verify_result_rotated": {dict of aspects->messages}

            # present only for errors (not invalid but real errors)
            "error_message":
        }

        Please note that invalid means that file is okay but not issued/tampered/etc
        but error means that the file is not OA file or API returns 500 errors
        """
        if self.request.POST.get("type") == "file":
            the_file = self.request.FILES["oa_file"]
            value = the_file.read()
            verify_result = self._unpack_and_verify_cleartext(value)
        elif self.request.POST.get("type") == "qrcode":
            the_code = self.request.POST.get("qrcode")
            try:
                verify_result = self._parse_and_verify_qrcode(the_code)
            except Exception as e:
                logger.exception(e)
                verify_result = {
                    "status": "error",
                    "error_message": "The QR code seems to be invalid or unsupported",
                }
        return verify_result

    def _unpack_and_verify_cleartext(self, cleartext):
        try:
            oa_verify_resp = self._verify_file(cleartext)
        except OaVerificationError as e:
            return {
                "status": "error",
                "error_message": str(e),
            }

        result = {}

        # the file has been verified and either valid or invalid, calculate the final status
        result["status"] = "valid"
        result["verify_result"] = oa_verify_resp.copy()
        result["verify_result_rotated"] = {}
        for row in oa_verify_resp:
            if row["status"].lower() == "invalid":
                result["status"] = "invalid"
            result["verify_result_rotated"][row.get("type")] = row

        if result["status"] == "valid":
            # worth further parsing only if the file is valid
            try:
                result["unwrapped_file"] = self._unwrap_file(cleartext)
                result["oa_raw_data"] = json.loads(cleartext)
            except Exception as e:
                logger.exception(e)
                # or likely our code has some bug or unsupported format in it
                raise OaVerificationError("Unable to unwrap the OA file - it's structure may be invalid")
            else:
                result["template_url"] = result["unwrapped_file"].get("data", {}).get("$template", {}).get("url")
                result["rendered"] = self.render_oa_document(
                    result["unwrapped_file"]
                )
                result["attachments"] = result["unwrapped_file"].get("data", {}).get("attachments") or []
        return result

    def render_oa_document(self, data):
        """
        This implementation is VERY dumb
        But we should call linked renderer (from the $template parameter)
        and return HTML code (or something to init that client-side)
        twice thinking about security of the solution
        """
        result = ""

        def render_flat_dict(key, value):

            if isinstance(value, dict):
                for subkey, subvalue in value.items():
                    rendered_value = render_flat_dict(subkey, subvalue)
            elif isinstance(value, list):
                if len(value) == 1:
                    value = value[0]
                    rendered_value = render_flat_dict("0", value)
                else:
                    for index, line in enumerate(value):
                        rendered_value = render_flat_dict(str(index), line)
            else:
                rendered_value = escape(value)
            rendered_key = f"<b>{key.capitalize()}</b>:" if key else ""
            return f"""
                <div style='border: 1px solid gray; padding-left: 20px; margin: 3px;'>
                    {rendered_key} {rendered_value}
                </div>
            """

        md = data["data"].copy()
        md.pop("attachments", None)

        for k, v in md.items():
            result += render_flat_dict(k, v) + "\n"

        result += ""
        return result

    def _unwrap_file(self, content):
        """
        Warning: it's unreliable but quick
        It's better to cal OA.unwrap() method
        """
        def unwrap_it(what):
            if isinstance(what, str):
                # wrapped something
                if what.count(":") >= 2:
                    uuidvalue, vtype, val = what.split(":", maxsplit=2)
                    if len(uuidvalue) == len("6cdb27f1-a46e-4dea-b1af-3b3faf7d983d"):
                        if vtype == "string":
                            return str(val)
                        elif vtype == "boolean":
                            return True if val.lower() == "true" else False
                        elif vtype == "number":
                            return int(val)
                        elif vtype == "null":
                            return None
                        elif vtype == "undefined":
                            return None
                    else:
                        return what
            elif isinstance(what, list):
                return [
                    unwrap_it(x) for x in what
                ]
            elif isinstance(what, dict):
                return {
                    k: unwrap_it(v)
                    for k, v
                    in what.items()
                }
            else:
                return what

        wrapped = json.loads(content)
        return unwrap_it(wrapped)

    def _verify_file(self, file_content):
        try:
            resp = requests.post(
                config.OA_VERIFY_API_URL,
                files={
                    "file": file_content,
                }
            )
        except Exception as e:
            raise OaVerificationError(
                f"Verifier temporary unavailable (error {e.__class__.__name__}); please try again later"
            )
        if resp.status_code == 200:
            # now it contains list of dicts, each tells us something
            # about one aspect of the OA document
            return resp.json()
        elif resp.status_code == 400:
            logger.warning("OA verify: %s %s", resp.status_code, resp.json())
            message = resp.json().get("error") or "unknown error"
            raise OaVerificationError(f"Verifier doesn't accept that file: {message}")
        else:
            logger.warning(
                "%s resp from the OA Verify endpoint - %s",
                resp.status_code, resp.content
            )
            raise OaVerificationError(
                f"Verifier temporary unavailable (error {resp.status_code}); please try again later"
            )

    def _parse_and_verify_qrcode(self, the_code):
        """
        2 kinds of QR codes:

        1. new one self-contained
        https://action.openattestation.com/?q={q}
        where q is urlencoded JSON something like
        {
            "type": "DOCUMENT",
            "payload": {
                "uri": "https://trade.c1.devnet.trustbridge.io/oa/1d490b1b-aee8-47f3-bfa5-d08c67e940eb/",
                "key": "DC97D0BA857D6FC213959F6F42E77AF0426C8329ABF3855B5000FED82B86E82C",
                "permittedActions": ["VIEW"],
                "redirect": "https://dev.tradetrust.io"
            }
        }

        2. old one, just tradetrust data
        tradetrust://{"uri":"https://trade.c1.devnet.trustbridge.io/oa/1d490b1b-aee8-47f3-bfa5-d08c67e940eb/#DC97D0BA857D6FC213959F6F42E77AF0426C8329ABF3855B5000FED82B86E82C"}

        Note we catch all exceptions one layer above, so no need to do it here

        """
        if the_code.startswith("https://") or the_code.startswith("http://"):
            # new approach
            components = urllib.parse.urlparse(the_code)
            params = urllib.parse.parse_qs(components.query)
            req = json.loads(params["q"][0])
            if req["type"].upper() == "DOCUMENT":
                uri = req["payload"]["uri"]
                key = req["payload"]["key"]  # it's always AES
        elif the_code.startswith("tradetrust://"):
            # old approach
            json_body = the_code.split("://", maxsplit=1)[1]
            params = json.loads(json_body)["uri"]
            uri, key = params.rsplit("#", maxsplit=1)
        else:
            raise OaVerificationError("Unsupported QR code format")

        # this will contain fields cipherText, iv, tag, type
        logger.info("Retrieving document %s having key %s", uri, key)

        try:
            document_info = requests.get(uri).json()["document"]
        except Exception as e:
            logger.exception(e)
            raise OaVerificationError(
                "Unable to download the OA document from given url (this usually "
                "means that remote service is down or acting incorrectly"
            )

        cp = AESCipher(key)
        cleartext_b64 = cp.decrypt(
            document_info["iv"],
            document_info["tag"],
            document_info["cipherText"],
        ).decode("utf-8")
        cleartext = base64.b64decode(cleartext_b64)

        logger.info("Unpacking document %s", uri)

        return self._unpack_and_verify_cleartext(cleartext)
