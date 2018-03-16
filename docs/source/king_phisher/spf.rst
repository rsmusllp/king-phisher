:mod:`spf`
==========

.. module:: king_phisher.spf
   :synopsis:

This module provides functionality for checking published Sender Policy
Framework (SPF) records. SPF is defined in :rfc:`7208`.

Data
----

.. autodata:: DEFAULT_DNS_TIMEOUT

.. autodata:: MACRO_REGEX
   :annotation:

.. autodata:: MAX_QUERIES

.. autodata:: MAX_QUERIES_VOID

.. autodata:: QUALIFIERS
   :annotation:

Functions
---------

.. autofunction:: check_host

.. autofunction:: validate_record

Classes
-------

.. autoclass:: SenderPolicyFramework
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: SPFDirective
   :special-members: __init__
   :undoc-members:

.. autoclass:: SPFMatch
   :special-members: __init__
   :undoc-members:

.. autoclass:: SPFRecord
   :special-members: __init__
   :undoc-members:

Exceptions
----------

.. autoexception:: SPFError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: SPFTempError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: SPFTimeOutError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: SPFParseError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: SPFPermError
   :members:
   :show-inheritance:
   :undoc-members:
