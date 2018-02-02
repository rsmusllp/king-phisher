:mod:`serializers`
==================

.. module:: king_phisher.serializers
   :synopsis:

This module provides a standardized interface for serializing objects using
different formats. The Serializers provided by this module are organized by
their format into different classes. The necessary methods for utilizing them
are all ``classmethod``'s making it unnecessary to create an instance of any
of them.

Functions
---------

.. autofunction:: from_elementtree_element

.. autofunction:: to_elementtree_subelement

Classes
-------

.. autoclass:: JSON
   :show-inheritance:
   :members:

.. autoclass:: MsgPack
   :show-inheritance:
   :members:

.. autoclass:: Serializer
   :show-inheritance:
   :members:
