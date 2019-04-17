:mod:`startup`
==============

.. module:: king_phisher.startup
   :synopsis:

This module provides generic functions for the early initialization of the
project's environment. This is primarily used for the management of external
dependencies.

.. note::
   This is a :ref:`"Clean Room" module <clean-room-modules>` and is suitable for
   use during initialization.

Functions
---------

.. autofunction:: argp_add_client

.. autofunction:: argp_add_default_args

.. autofunction:: argp_add_server

.. autofunction:: pipenv_entry

.. autofunction:: run_process

.. autofunction:: start_process

.. autofunction:: which

Classes
-------

.. autoclass:: ProcessResults
