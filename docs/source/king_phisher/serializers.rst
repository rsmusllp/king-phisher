:mod:`serializers`
==================

.. module:: serializers
   :synopsis:

This module provides a standardized interface for serializing objects using
different formats. The Serializers provided by this module are organized by
their format into different classes. The necessary methods for utilizing them
are all ``classmethod``'s making it unnecessary to create an instance of any
of them.

Functions
---------

.. autofunction:: king_phisher.serializers.from_elementtree_element

.. autofunction:: king_phisher.serializers.to_elementtree_subelement

Classes
-------

.. autoclass:: king_phisher.serializers.JSON
   :show-inheritance:
   :members:

.. autoclass:: king_phisher.serializers.MsgPack
   :show-inheritance:
   :members:

.. autoclass:: king_phisher.serializers.Serializer
   :show-inheritance:
   :members:
