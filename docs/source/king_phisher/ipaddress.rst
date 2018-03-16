:mod:`ipaddress`
================

.. module:: king_phisher.ipaddress
   :synopsis:

This module provides functionality for dealing with an external "ipaddress"
module in a Python 2 backwards compatible way. In Python 2 all string address
arguments are converted to unicode which removes the ability to specify
addresses as packed binary strings.

Functions
---------

.. autofunction:: ip_address

.. autofunction:: ip_network

.. autofunction:: ip_interface

.. autofunction:: is_loopback

.. autofunction:: is_valid

Classes
-------

.. autoclass:: IPv4Address
   :members:

.. autoclass:: IPv4Network
   :members:

.. autoclass:: IPv6Address
   :members:

.. autoclass:: IPv6Network
   :members:
