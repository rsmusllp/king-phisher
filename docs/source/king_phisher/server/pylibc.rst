:mod:`pylibc`
=============

.. module:: king_phisher.server.pylibc
   :synopsis:

This module provides a wrapped interface for Linux's libc. Most of this
functionality is duplicated in Python's own :py:mod:`grp` and :py:mod:`pwd`
modules. This implementation however, using :py:mod:`ctypes` to directly
interface with libc is necessary to avoid dead-lock issues when authenticating
non-local users such as would be found in an environment using an LDAP server.

Functions
---------

.. autofunction:: getgrnam

.. autofunction:: getgrouplist

.. autofunction:: getpwnam

.. autofunction:: getpwuid