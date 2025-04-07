import re
import requests
import urllib.parse

import frappe
from frappe import _

from frappe.utils import cint
from frappe.core.doctype.file.file import File
from frappe.core.doctype.file.utils import decode_file_content
from frappe_s3_attachment.controller import extract_key_and_file_name

class FileOverride(File):
    def set_is_private(self):
        if self.file_url:
             self.is_private = cint(
                self.file_url.startswith("/private") or
                "frappe_s3_attachment.controller.generate_file" in self.file_url
            )

    def set_file_name(self):
        if not self.file_name and not self.file_url:
            frappe.throw(
                _("Fields `file_name` or `file_url` must be set for File"), exc=frappe.MandatoryError
            )
        elif not self.file_name and self.file_url:
            if "frappe_s3_attachment.controller.generate_file" in self.file_url:
                parsed_url = urllib.parse.urlparse(self.file_url)
                query_params = urllib.parse.parse_qs(parsed_url.query)

                if "file_name" in query_params:
                    self.file_name = query_params["file_name"][0]
                else:
                    self.file_name = parsed_url.path.split("/")[-1]
            else:
                self.file_name = self.file_url.split("/")[-1]
                parts = self.file_name.split("_")
                if len(parts) > 1:
                    self.file_name = "_".join(parts[1:])
        else:
            self.file_name = re.sub(r"/", "", self.file_name)

    def get_content(self):
        if self.is_folder:
            frappe.throw(_("Cannot get file contents of a Folder"))

        if self.file_url and self.file_url.startswith(("http://", "https://")):
            self.validate_file_url()
            file_path = self.file_url

            if "frappe_s3_attachment.controller.generate_file" in file_path:
                site_base_url = frappe.utils.get_url()
                key, file_name = extract_key_and_file_name(file_path)
                signed_url_request = f"{site_base_url}/api/method/frappe_s3_attachment.controller.generate_signed_url?key={key}&file_name={file_name}"
                response = requests.get(signed_url_request)

                if response.status_code == 200:
                    file_path = response.json().get("message")
                else:
                    frappe.throw(f"Failed to generate signed URL: {response.status_code}")

            response = requests.get(file_path)
            if response.status_code == 200:
                self._content = response.content
            else:
                frappe.throw(f"Failed to get file from {file_path} (Status: {response.status_code})")
        else:
            if self.get("content"):
                self._content = self.content
                if self.decode:
                    self._content = decode_file_content(self._content)
                    self.decode = False
                return self._content

            file_path = self.get_full_path()
            with open(file_path, mode="rb") as f:
                self._content = f.read()

        try:
            # for plain text files
            self._content = self._content.decode()
        except UnicodeDecodeError:
            # for .png, .jpg, etc
            pass

        return self._content