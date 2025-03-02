import re
import urllib.parse

import frappe
from frappe import _

from frappe.utils import call_hook_method, cint, get_files_path, get_hook_method, get_url
from frappe.core.doctype.file.file import File

frappe.utils.logger.set_log_level("DEBUG")
logger = frappe.logger("api", allow_site=True, file_count=50)

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