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

from sphinx import addnodes
from sphinx.directives import ObjectDescription
from sphinx.domains import Domain
from sphinx.roles import XRefRole
from sphinx.util.nodes import make_refnode
from sphinx.util import ws_re

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

class GenericObjectBase(ObjectDescription):
	def before_content(self):
		if self.names:
			self.env.ref_context[self.xref_attribute] = self.names[-1]

	def after_content(self):
		self.env.ref_context.pop(self.xref_attribute)

	def add_target_and_index(self, name, sig, signode):
		targetname = '%s:%s-%s' % (self.xref_prefix, self.objtype, name)
		signode['ids'].append(targetname)
		self.state.document.note_explicit_target(signode)
		self.env.domaindata[self.domain]['objects'][self.objtype, name] = self.env.docname, targetname
		self.indexnode['entries'].append(('single', "{} ({})".format(name, self.label), targetname, '', None))

	def handle_signature(self, sig, signode):
		signode.clear()
		signode += addnodes.desc_name(sig, sig)
		return ws_re.sub('', sig)

	@property
	def xref_attribute(self):
		return self.xref_prefix + ':' + self.attribute

class XRefRoleBase(XRefRole):
	def process_link(self, env, refnode, has_explicit_title, title, target):
		refnode[self.xref_attribute] = env.ref_context.get(self.xref_attribute)
		if not has_explicit_title:
			title = title.lstrip('.')    # only has a meaning for the target
			target = target.lstrip('~')  # only has a meaning for the title
			# if the first character is a tilde, don't display the module/class
			# parts of the contents
			if title[0:1] == '~':
				title = title[1:]
				dot = title.rfind('.')
				if dot != -1:
					title = title[dot + 1:]
		# if the first character is a dot, search more specific namespaces first
		# else search builtins first
		if target[0:1] == '.':
			target = target[1:]
			refnode['refspecific'] = True
		return title, target

	@property
	def xref_attribute(self):
		return self.xref_prefix + ':' + self.attribute

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
