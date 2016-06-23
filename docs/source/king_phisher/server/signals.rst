:mod:`server.signals`
=====================

.. module:: server.signals
   :synopsis:

This module contains the signals which are used by the server to dispatch
events. Additional signal details regarding how these signals are used is
available in the :ref:`server-signals-label` documentation.

Functions
---------

.. autofunction:: king_phisher.server.signals.safe_send

Signals
-------

.. autodata:: king_phisher.server.signals.credentials_received
   :annotation:

.. autodata:: king_phisher.server.signals.db_initialized
   :annotation:

.. autodata:: king_phisher.server.signals.db_session_deleted
   :annotation:

.. autodata:: king_phisher.server.signals.db_session_inserted
   :annotation:

.. autodata:: king_phisher.server.signals.db_session_updated
   :annotation:

.. autodata:: king_phisher.server.signals.db_table_delete
   :annotation:

.. autodata:: king_phisher.server.signals.db_table_insert
   :annotation:

.. autodata:: king_phisher.server.signals.db_table_update
   :annotation:

.. autodata:: king_phisher.server.signals.request_received
   :annotation:

.. autodata:: king_phisher.server.signals.rpc_method_call
   :annotation:

.. autodata:: king_phisher.server.signals.rpc_method_called
   :annotation:

.. autodata:: king_phisher.server.signals.rpc_user_logged_in
   :annotation:

.. autodata:: king_phisher.server.signals.rpc_user_logged_out
   :annotation:

.. autodata:: king_phisher.server.signals.server_initialized
   :annotation:

.. autodata:: king_phisher.server.signals.visit_received
   :annotation:
