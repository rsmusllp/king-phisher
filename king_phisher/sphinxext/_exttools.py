#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  king_phisher/sphinxext/_exttools.py
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

from docutils import nodes

from sphinx.domains import Domain
from sphinx.util.nodes import make_refnode

class ArgumentBase(nodes.Part, nodes.Inline, nodes.TextElement):
	pass

class ArgumentListBase(nodes.Part, nodes.Inline, nodes.TextElement):
	child_text_separator = ' '

class DomainBase(Domain):
	name = None
	label = None
	object_types = {}
	directives = {}
	roles = {}
	initial_data = {
		'objects': {},  # (type, name) -> docname, labelid
	}
	dangling_warnings = {}
	def clear_doc(self, docname):
		if 'objects' in self.data:
			for key, (fn, _) in list(self.data['objects'].items()):
				if fn == docname:
					del self.data['objects'][key]

	def resolve_xref(self, env, fromdocname, builder, typ, target, node, contnode):
		objtypes = self.objtypes_for_role(typ) or []
		for objtype in objtypes:
			if (objtype, target) in self.data['objects']:
				docname, labelid = self.data['objects'][objtype, target]
				break
		else:
			docname, labelid = '', ''
		if not docname:
			return None
		return make_refnode(builder, fromdocname, docname, labelid, contnode)

	def get_objects(self):
		for (type, name), info in self.data['objects'].items():
			yield (name, name, type, info[0], info[1], self.object_types[type].attrs['searchprio'])

	def get_type_name(self, type, primary=False):
		# never prepend "Default"
		return type.lname

def argument_visit(self, node):
	pass

def argument_depart(self, node):
	pass

def argument_list_visit(self, node):
	self.visit_desc_parameterlist(node)

def argument_list_depart(self, node):
	self.depart_desc_parameterlist(node)

def html_argument_visit(self, node):
	self.body.append('<span class="arg">')

def html_argument_depart(self, node):
	self.body.append('</span>')

def html_argument_list_visit(self, node):
	self.visit_desc_parameterlist(node)
	if len(node.children) > 3:
		self.body.append('<span class="long-argument-list">')
	else:
		self.body.append('<span class="argument-list">')

def html_argument_list_depart(self, node):
	self.body.append('</span>')
	self.depart_desc_parameterlist(node)

def add_app_node_arguments(app, argument_node, argument_list_node):
	app.add_node(
		node=argument_list_node,
		html=(html_argument_list_visit, html_argument_list_depart),
		latex=(argument_list_visit, argument_list_depart)
	)
	app.add_node(
		node=argument_node,
		html=(html_argument_visit, html_argument_depart),
		latex=(argument_visit, argument_depart)
	)
