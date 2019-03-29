#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/sphinxext/graphql.py
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

import re

from docutils import nodes
from sphinx import addnodes
from sphinx.util import docfields
from king_phisher.third_party.domaintools import custom_domain

http_sig_param_re = re.compile(r'\((?:(?P<type>[^:)]+):)?(?P<name>[\w_]+)\)', re.VERBOSE)

class DescGraphQLField(nodes.Part, nodes.Inline, nodes.TextElement):
	"""Node for an field wrapper"""

class DescGraphQLFieldList(nodes.Part, nodes.Inline, nodes.TextElement):
	"""Node for a general field list."""
	child_text_separator = ' '

def argument_visit(self, node):
	pass

def argument_depart(self, node):
	pass

def html_field_visit(self, node):
	self.body.append('<span class="arg">')

def html_field_depart(self, node):
	self.body.append('</span>')

def fieldlist_visit(self, node):
	self.visit_desc_parameterlist(node)

def fieldlist_depart(self, node):
	self.depart_desc_parameterlist(node)

def html_fieldlist_visit(self, node):
	self.visit_desc_parameterlist(node)
	if len(node.children) > 3:
		self.body.append('<span class="long-argument-list">')
	else:
		self.body.append('<span class="argument-list">')

def html_fieldlist_depart(self, node):
	self.body.append('</span>')
	self.depart_desc_parameterlist(node)

def parse_macro(env, sig, signode):
	m = re.match(r'([a-zA-Z0-9_/\(\):]+)\(([a-zA-Z0-9,\'"_= ]*)\)', sig)
	if not m:
		signode += addnodes.desc_name(sig, sig)
		return sig
	uri_path, args = m.groups()
	return uri_path

def setup(app):
	app.add_node(
		node=DescGraphQLFieldList,
		html=(html_fieldlist_visit, html_fieldlist_depart),
		latex=(fieldlist_visit, fieldlist_depart)
	)
	app.add_node(
		node=DescGraphQLField,
		html=(html_field_visit, html_field_depart),
		latex=(argument_visit, argument_depart)
	)
	app.add_domain(custom_domain(
		'GraphQLDomain',
		name='gql',
		label='GraphQL',
		elements=dict(
			object=dict(
				objname='GraphQL Object',
				indextemplate=None,
				parse=parse_macro,
				role='obj',
				fields=(
					docfields.TypedField(
						'field',
						label='Fields',
						names=('field',),
						typenames=('fieldtype', 'type')
					),
				)
			)
		)
	))
