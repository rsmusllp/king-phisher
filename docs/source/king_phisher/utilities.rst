:mod:`utilities`
================

.. module:: king_phisher.utilities
   :synopsis:

This module collects various useful utility functions that are used throughout
the application.

Functions
---------

.. autofunction:: argp_add_args

.. autofunction:: assert_arg_type

.. autofunction:: configure_stream_logger

.. autofunction:: datetime_local_to_utc

.. autofunction:: datetime_utc_to_local

.. autofunction:: format_datetime

.. autofunction:: is_valid_email_address

.. autofunction:: make_message_uid

.. autofunction:: make_visit_uid

.. autofunction:: nonempty_string

.. autofunction:: open_uri

.. autofunction:: parse_datetime

.. autofunction:: password_is_complex

.. autofunction:: random_string

.. autofunction:: random_string_lower_numeric

.. autofunction:: switch

.. autofunction:: validate_json_schema

Classes
-------

.. autoclass:: Event
   :show-inheritance:
   :members:

.. autoclass:: FreezableDict
   :show-inheritance:
   :members:

.. autoclass:: PrefixLoggerAdapter
   :show-inheritance:
   :members:
   :special-members: __init__

.. autoclass:: Mock
   :show-inheritance:

.. autoclass:: Thread