# -*- coding: utf-8 -*-
"""
    sphinxcontrib.domaintools
    =========================

    Code is taken from `sphinx.domains.std`_ and is 
    parameterized for easy domain creation.

    :copyright: Kay-Uwe (Kiwi) Lorenz, ModuleWorks GmbH
    :license: BSD, see LICENSE.txt for details


    sphinx.domains.std
    ~~~~~~~~~~~~~~~~~~

    The standard domain.

    :copyright: Copyright 2007-2011 by the Sphinx team, see AUTHORS.
    :license: BSD, see LICENSE for details.
"""

import re
import unicodedata

from docutils import nodes

from sphinx import addnodes
from sphinx.roles import XRefRole
from sphinx.locale import l_, _
from sphinx.domains import Domain, ObjType
from sphinx.directives import ObjectDescription
from sphinx.util import ws_re
from sphinx.util.nodes import clean_astext, make_refnode

__version__ = '0.1.1'


class GenericObject(ObjectDescription):
    """
    #  A generic x-ref directive registered with Sphinx.add_object_type().

    Usage:
        DomainObject = type('DomainObject', (GenericObject, object), dict(
            domain = 'my-domain-name'))

        DomainObject = type('DomainObject', (GenericObject, object), dict(
            domain = 'my-domain-name', indextemplate=(

        class MyDescriptionObject(GenericObject):
    
    """
    indextemplate = ''
    parse_node = None
    domain = 'std'

    def handle_signature(self, sig, signode):
        if self.parse_node:
            name = self.parse_node(self.env, sig, signode)
        else:
            signode.clear()
            signode += addnodes.desc_name(sig, sig)
            # normalize whitespace like XRefRole does
            name = ws_re.sub('', sig)
        return name

    def add_target_and_index(self, name, sig, signode):
        targetname = '%s-%s' % (self.objtype, name)
        signode['ids'].append(targetname)
        self.state.document.note_explicit_target(signode)
        if self.indextemplate:
            colon = self.indextemplate.find(':')
            if colon != -1:
                indextype = self.indextemplate[:colon].strip()
                indexentry = self.indextemplate[colon+1:].strip() % (name,)
            else:
                indextype = 'single'
                indexentry = self.indextemplate % (name,)
            self.indexnode['entries'].append((indextype, indexentry,
                                              targetname, ''))
        self.env.domaindata[self.domain]['objects'][self.objtype, name] = \
            self.env.docname, targetname

class CustomDomain(Domain):
    """
    Domain for all objects that don't fit into another domain or are added
    via the application interface.
    """

    name = 'std'
    label = 'Default'

    object_types = {
    }

    directives = {
    }
    roles = {
    }

    initial_data = {
        'objects': {},      # (type, name) -> docname, labelid
    }

    dangling_warnings = {
    }

    def clear_doc(self, docname):
      if 'objects' in self.data:
       
        for key, (fn, _) in list(self.data['objects'].items()):
            if fn == docname:
                del self.data['objects'][key]

    def resolve_xref(self, env, fromdocname, builder,
                     typ, target, node, contnode):
        objtypes = self.objtypes_for_role(typ) or []
        for objtype in objtypes:
            if (objtype, target) in self.data['objects']:
                docname, labelid = self.data['objects'][objtype, target]
                break
        else:
            docname, labelid = '', ''
        if not docname:
            return None
        return make_refnode(builder, fromdocname, docname,
                            labelid, contnode)

    def get_objects(self):
        for (type, name), info in self.data['objects'].items():
            yield (name, name, type, info[0], info[1],
                   self.object_types[type].attrs['searchprio'])

    def get_type_name(self, type, primary=False):
        # never prepend "Default"
        return type.lname


def custom_domain(class_name, name='', label='', elements = {}):
    '''create a custom domain

    For each given element there are created a directive and a role
    for referencing and indexing.

    :param class_name: ClassName of your new domain (e.g. `GnuMakeDomain`)
    :param name      : short name of your domain (part of directives, e.g. `make`)
    :param label     : Long name of your domain (e.g. `GNU Make`)
    :param elements  :
        dictionary of your domain directives/roles

        An element value is a dictionary with following possible entries:

        - `objname` - Long name of the entry, defaults to entry's key

        - `role` - role name, defaults to entry's key

        - `indextemplate` - e.g. ``pair: %s; Make Target``, where %s will be 
          the matched part of your role.  You may leave this empty, defaults 
          to ``pair: %s; <objname>``

        - `parse_node` - a function with signature ``(env, sig, signode)``,
          defaults to `None`.

        - `fields` - A list of fields where parsed fields are mapped to. this
          is passed to Domain as `doc_field_types` parameter.

        - `ref_nodeclass` - class passed as XRefRole's innernodeclass,
          defaults to `None`.

    '''
    domain_class = type(class_name, (CustomDomain, object), dict(
        name  = name,
        label = label,
    ))

    domain_object_class = \
        type("%s_Object"%name, (GenericObject, object), dict(domain=name))

    for n,e in elements.items():
        obj_name = e.get('objname', n)
        domain_class.object_types[n] = ObjType(
            obj_name, e.get('role', n) )

        domain_class.directives[n] = type(n, (domain_object_class, object), dict(
            indextemplate   = e.get('indextemplate', 'pair: %%s; %s' % obj_name),
            parse_node      = staticmethod(e.get('parse', None)),
            doc_field_types = e.get('fields', []),
            ))

        domain_class.roles[e.get('role', n)] = XRefRole(innernodeclass=
            e.get('ref_nodeclass', None))

    return domain_class

