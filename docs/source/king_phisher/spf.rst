:mod:`spf`
==========

.. module:: spf
   :synopsis:

This module provides functionality for checking published Sender Policy
Framework (SPF) records. SPF is defined in :rfc:`7208`.

Data
----

.. autodata:: king_phisher.spf.MACRO_REGEX
   :annotation:

.. autodata:: king_phisher.spf.MAX_QUERIES

.. autodata:: king_phisher.spf.MAX_QUERIES_VOID

.. autodata:: king_phisher.spf.QUALIFIERS
   :annotation:

Functions
---------

.. autofunction:: king_phisher.spf.check_host

.. autofunction:: king_phisher.spf.validate_record

Classes
-------

.. autoclass:: king_phisher.spf.SenderPolicyFramework
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: king_phisher.spf.SPFDirective
   :special-members: __init__
   :undoc-members:

.. autoclass:: king_phisher.spf.SPFMatch
   :special-members: __init__
   :undoc-members:

.. autoclass:: king_phisher.spf.SPFRecord
   :special-members: __init__
   :undoc-members:

Exceptions
----------

.. autoexception:: king_phisher.spf.SPFError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: king_phisher.spf.SPFTempError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: king_phisher.spf.SPFParseError
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: king_phisher.spf.SPFPermError
   :members:
   :show-inheritance:
   :undoc-members:
