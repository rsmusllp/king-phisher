:mod:`AdvancedHTTPServer`
=========================

.. module:: king_phisher.third_party.AdvancedHTTPServer
   :synopsis: Python HTTP Server

AdvancedHTTPServer is a light weight module that provides a set of classes
for quickly making HTTP servers for a variety of purposes. It focuses on
a light and powerful design with an emphasis on portability. It was
designed after and builds upon Python's standard :py:mod:`BaseHTTPServer`
module. AdvancedHTTPServer is released under the BSD license and can be
freely distributed and packaged with other software.

Data
----

.. data:: SERIALIZER_DRIVERS
   :annotation:

Functions
---------

.. autofunction:: build_server_from_argparser

.. autofunction:: build_server_from_config

.. autofunction:: random_string

.. autofunction:: resolve_ssl_protocol_version

Classes
-------

.. autoclass:: AdvancedHTTPServer
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServerRegisterPath
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServerRequestHandler
   :members:

.. autoclass:: AdvancedHTTPServerRPCClient
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServerRPCClientCached
   :members:
   :undoc-members:

.. autoclass:: AdvancedHTTPServerSerializer
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServerTestCase
   :members:

Exceptions
----------

.. autoexception:: AdvancedHTTPServerRPCError
   :members:
   :undoc-members:
