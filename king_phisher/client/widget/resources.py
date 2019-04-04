#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/client/widget/resources.py
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

from king_phisher.client import gui_utilities
from king_phisher.constants import ColorHexCode

from gi.repository import Gtk
from gi.repository import Pango

font_desc_italic = Pango.FontDescription()
"""
A :py:class:`Pango.FontDescription` configured for representing italicized text.
"""
font_desc_italic.set_style(Pango.Style.ITALIC)

renderer_text_desc = Gtk.CellRendererText()
"""
A :py:class:`Gtk.CellRendererText` instance which is configured to be suitable
for showing descriptions of various object.
"""
renderer_text_desc.set_property('ellipsize', Pango.EllipsizeMode.END)
renderer_text_desc.set_property('font-desc', font_desc_italic)
renderer_text_desc.set_property('foreground', ColorHexCode.GRAY)
renderer_text_desc.set_property('max-width-chars', 20)

class CompanyEditorGrid(gui_utilities.GladeProxy):
	"""
	An embeddable widget which contains the necessary widgets to edit the
	various fields of a company object.
	"""
	name = 'CompanyEditorGrid'
	"""The name of the top level widget in the GTK Builder data file."""
	children = (
		'combobox_company_industry',
		'entry_company_industry',
		'entry_company_name',
		'entry_company_description',
		'entry_company_url_main',
		'entry_company_url_email',
		'entry_company_url_remote_access'
	)
	"""The children widgets that can be used to edit the fields of the company."""

class ManagedTreeView(gui_utilities.GladeProxy):
	pass
