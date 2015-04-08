#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/dialogs/exception.py
#
#  Redistribution and use in source and binary forms, with or without
#  modification, are permitted provided that the following conditions are
#  met:
#
#  * Redistributions of source code must retain the above copyright
#    notice, this list of conditions and the following disclaimer.
#  * Redistributions in binary form must reproduce the above
#    copyright notice, this list of conditions and the following disclaimer
#    in the documentation and/or other materials provided with the
#    distribution.
#  * Neither the name of the project nor the names of its
#    contributors may be used to endorse or promote products derived from
#    this software without specific prior written permission.
#
#  THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
#  "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
#  LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
#  A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
#  OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
#  SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
#  LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
#  DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
#  THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
#  (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
#  OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
#

import platform
import sys
import traceback

from king_phisher import version
from king_phisher.client import gui_utilities

__all__ = ['ExceptionDialog']

EXCEPTION_DETAILS_TEMPLATE = """
Error Type: {error_type}
Error Details: {error_details}
King Phisher Version: {king_phisher_version}
Platform Version: {platform_version}
Python Version: {python_version}

{stack_trace}
"""

class ExceptionDialog(gui_utilities.UtilityGladeGObject):
	"""
	Display a dialog which shows an error message for a python exception.
	The dialog includes useful details for reporting and debugging the exception
	which occurred.
	"""
	top_gobject = 'dialog'
	def __init__(self, config, parent, exc_info=None):
		"""
		:param dict config: The King Phisher client configuration.
		:param parent: The parent window for this object.
		:type parent: :py:class:`Gtk.Window`
		:param tuple exc_info: The exception information as provided by :py:func:`sys.exc_info`.
		"""
		super(ExceptionDialog, self).__init__(config, parent)
		self.error_description = self.gtk_builder_get('label_error_description')
		self.error_details = self.gtk_builder_get('textview_error_details')
		self.exc_info = exc_info or sys.exc_info()

	def interact(self):
		exc_type, exc_value, exc_traceback = self.exc_info
		pversion = 'UNKNOWN'
		if sys.platform.startswith('linux'):
			pversion = 'Linux: ' + ' '.join(platform.linux_distribution())
		elif sys.platform.startswith('win'):
			pversion = 'Windows: ' + ' '.join(platform.win32_ver())
			if getattr(sys, 'frozen', False):
				pversion += ' (Frozen=True)'
			else:
				pversion += ' (Frozen=False)'
		exc_name = "{0}.{1}".format(exc_type.__module__, exc_type.__name__)
		details = EXCEPTION_DETAILS_TEMPLATE.format(
			error_details=repr(exc_value),
			error_type=exc_name,
			platform_version=pversion,
			python_version="{0}.{1}.{2}".format(*sys.version_info),
			king_phisher_version=version.version,
			stack_trace=''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
		)
		details = details.strip()

		self.error_description.set_text("Error type: {0}".format(exc_name))
		self.error_details.get_buffer().set_text(details)

		self.dialog.show_all()
		self.dialog.run()
		self.dialog.destroy()
		return
