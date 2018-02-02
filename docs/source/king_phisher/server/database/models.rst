:mod:`models`
=============

.. module:: king_phisher.server.database.models
   :synopsis:

This module provides the models for the data stored in the database as well as
functionality for defining and managing the models themselves.

Data
----

.. autodata:: database_tables
   :annotation:

.. autodata:: SCHEMA_VERSION
   :annotation:

Functions
---------

.. autofunction:: current_timestamp

.. autofunction:: get_tables_with_column_id

.. autofunction:: register_table

Classes
-------

.. autoclass:: BaseRowCls
   :show-inheritance:
   :members:

.. autoclass:: MetaTable
   :show-inheritance:
