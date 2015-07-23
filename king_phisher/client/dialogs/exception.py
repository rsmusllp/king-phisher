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

from king_phisher import its
from king_phisher import version
from king_phisher.client import gui_utilities
from king_phisher.third_party import AdvancedHTTPServer

from gi.repository import Gtk

__all__ = ['ExceptionDialog']

EXCEPTION_DETAILS_TEMPLATE = """
Error Type: {error_type}
Error Details: {error_details}
Error UID: {error_uid}
RPC Error: {rpc_error_details}
King Phisher Version: {king_phisher_version}
Platform Version: {platform_version}
Python Version: {python_version}
Gtk Version: {gtk_version}

{stack_trace}
"""

class ExceptionDialog(gui_utilities.GladeGObject):
	"""
	Display a dialog which shows an error message for a python exception.
	The dialog includes useful details for reporting and debugging the exception
	which occurred.
	"""
	top_gobject = 'dialog'
	def __init__(self, application, exc_info=None, error_uid=None):
		"""
		:param application: The parent application for this object.
		:type application: :py:class:`Gtk.Application`
		:param tuple exc_info: The exception information as provided by :py:func:`sys.exc_info`.
		:param str error_uid: An optional unique identifier for the exception that can be provided for tracking purposes.
		"""
		super(ExceptionDialog, self).__init__(application)
		self.error_description = self.gtk_builder_get('label_error_description')
		self.error_details = self.gtk_builder_get('textview_error_details')
		self.exc_info = exc_info or sys.exc_info()
		self.error_uid = error_uid

	def interact(self):
		exc_type, exc_value, exc_traceback = self.exc_info
		pversion = 'UNKNOWN'
		if its.on_linux:
			pversion = 'Linux: ' + ' '.join(platform.linux_distribution())
		elif its.on_windows:
			pversion = 'Windows: ' + ' '.join(platform.win32_ver())
			if its.frozen:
				pversion += ' (Frozen=True)'
			else:
				pversion += ' (Frozen=False)'
		exc_name = "{0}.{1}".format(exc_type.__module__, exc_type.__name__)
		rpc_error_details = 'N/A (Not an RPC error)'
		if isinstance(exc_value, AdvancedHTTPServer.AdvancedHTTPServerRPCError):
			rpc_error_details = "Name: {0}".format(exc_value.remote_exception['name'])
			if exc_value.remote_exception.get('message'):
				rpc_error_details += " Message: '{0}'".format(exc_value.remote_exception['message'])
		details = EXCEPTION_DETAILS_TEMPLATE.format(
			error_details=repr(exc_value),
			error_type=exc_name,
			error_uid=(self.error_uid or 'N/A'),
			rpc_error_details=rpc_error_details,
			king_phisher_version=version.version,
			platform_version=pversion,
			python_version="{0}.{1}.{2}".format(*sys.version_info),
			gtk_version="{0}.{1}.{2}".format(Gtk.get_major_version(), Gtk.get_minor_version(), Gtk.get_micro_version()),
			stack_trace=''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
		)
		details = details.strip() + '\n'

		if exc_name.startswith('king_phisher.third_party.'):
			exc_name = exc_name[25:]
		self.error_description.set_text("Error type: {0}".format(exc_name))
		self.error_details.get_buffer().set_text(details)

		self.dialog.show_all()
		self.dialog.run()
		self.dialog.destroy()
		return
