:mod:`AdvancedHTTPServer` --- Light and flexible web framework
==============================================================

.. module:: AdvancedHTTPServer
   :synopsis: Light and flexible web framework

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

.. autofunction:: AdvancedHTTPServer.build_server_from_argparser

.. autofunction:: AdvancedHTTPServer.build_server_from_config

.. autofunction:: AdvancedHTTPServer.random_string

Classes
-------

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServer
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServerRegisterPath
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServerRequestHandler
   :members:

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServerRESTAPI
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServerRPCClient
   :members:
   :special-members: __init__
   :undoc-members:

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServerRPCClientCached
   :members:
   :undoc-members:

.. autoclass:: AdvancedHTTPServer.AdvancedHTTPServerTestCase
   :members:

Exceptions
----------

.. autoexception:: AdvancedHTTPServer.AdvancedHTTPServerRPCError
   :members:
   :undoc-members:
