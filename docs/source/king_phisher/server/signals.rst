:mod:`signals`
==============

.. module:: king_phisher.server.signals
   :synopsis:

This module contains the signals which are used by the server to dispatch
events. Additional signal details regarding how these signals are used is
available in the :ref:`server-signals-label` documentation.

Functions
---------

.. autofunction:: send_safe

Signals
-------

.. autodata:: campaign_alert
   :annotation:

.. autodata:: credentials_received
   :annotation:

.. autodata:: db_initialized
   :annotation:

.. autodata:: db_session_deleted
   :annotation:

.. autodata:: db_session_inserted
   :annotation:

.. autodata:: db_session_updated
   :annotation:

.. autodata:: db_table_delete
   :annotation:

.. autodata:: db_table_insert
   :annotation:

.. autodata:: db_table_update
   :annotation:

.. autodata:: email_opened
   :annotation:

.. autodata:: request_handle
   :annotation:

.. autodata:: request_received
   :annotation:

.. autodata:: response_sent
   :annotation:

.. autodata:: rpc_method_call
   :annotation:

.. autodata:: rpc_method_called
   :annotation:

.. autodata:: rpc_user_logged_in
   :annotation:

.. autodata:: rpc_user_logged_out
   :annotation:

.. autodata:: server_initialized
   :annotation:

.. autodata:: visit_received
   :annotation:
