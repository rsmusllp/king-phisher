:mod:`catalog`
==============

.. module:: king_phisher.catalog
   :synopsis:

This module provides functionality for processing and working with data
published on the available add ons for the application.

Overview
--------

The classes within this module are primarily for organizing the large amount of
data describing published add ons. This information is broken down into the
various objects in a hierarchy where the parent contain zero or more children
objects. In this sense the hierarchy is a tree data structure where the nodes
are different data types such as catalogs, repositories, collections etc.

The hierarchy of these objects is as follows in order of parent to children:

* :py:class:`.CatalogManager`
* :py:class:`.Catalog`
* :py:class:`.Repository`
* :py:class:`.Collection`
* :py:class:`.CollectionItemFile`

Data
----

.. autodata:: COLLECTION_TYPES
   :annotation:

Functions
---------

.. autofunction:: sign_item_files

Classes
-------

.. autoclass:: Catalog
   :show-inheritance:
   :members:
   :inherited-members:
   :special-members: __init__

.. autoclass:: CatalogManager
   :show-inheritance:
   :members:
   :inherited-members:
   :special-members: __init__

.. autoclass:: Collection
   :show-inheritance:
   :members:
   :special-members: __init__

.. autoclass:: CollectionItemFile
   :members:
   :special-members: __init__

.. autoclass:: Repository
   :show-inheritance:
   :members:
   :inherited-members:
   :special-members: __init__
