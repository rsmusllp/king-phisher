:mod:`server.server_rpc`
========================

.. module:: server.server_rpc
   :synopsis:

This module provides the RPC server functionality that is used by the client
to communicate with the server application.

Data
----

.. autodata:: king_phisher.server.server_rpc.CONFIG_READABLE
   :annotation:

.. autodata:: king_phisher.server.server_rpc.CONFIG_WRITEABLE
   :annotation:

.. autodata:: king_phisher.server.server_rpc.RPC_AUTH_HEADER

.. autodata:: king_phisher.server.server_rpc.VIEW_ROW_COUNT

Functions
---------

.. autofunction:: king_phisher.server.server_rpc.register_rpc

.. autofunction:: king_phisher.server.server_rpc.rpc_campaign_alerts_is_subscribed

.. autofunction:: king_phisher.server.server_rpc.rpc_campaign_alerts_subscribe

.. autofunction:: king_phisher.server.server_rpc.rpc_campaign_alerts_unsubscribe

.. autofunction:: king_phisher.server.server_rpc.rpc_campaign_landing_page_new

.. autofunction:: king_phisher.server.server_rpc.rpc_campaign_message_new

.. autofunction:: king_phisher.server.server_rpc.rpc_campaign_new

.. autofunction:: king_phisher.server.server_rpc.rpc_config_get

.. autofunction:: king_phisher.server.server_rpc.rpc_config_set

.. autofunction:: king_phisher.server.server_rpc.rpc_database_count_rows

.. autofunction:: king_phisher.server.server_rpc.rpc_database_delete_row_by_id

.. autofunction:: king_phisher.server.server_rpc.rpc_database_delete_rows_by_id

.. autofunction:: king_phisher.server.server_rpc.rpc_database_get_row_by_id

.. autofunction:: king_phisher.server.server_rpc.rpc_database_insert_row

.. autofunction:: king_phisher.server.server_rpc.rpc_database_set_row_value

.. autofunction:: king_phisher.server.server_rpc.rpc_database_view_rows

.. autofunction:: king_phisher.server.server_rpc.rpc_geoip_lookup

.. autofunction:: king_phisher.server.server_rpc.rpc_geoip_lookup_multi

.. autofunction:: king_phisher.server.server_rpc.rpc_login

.. autofunction:: king_phisher.server.server_rpc.rpc_logout

.. autofunction:: king_phisher.server.server_rpc.rpc_ping

.. autofunction:: king_phisher.server.server_rpc.rpc_shutdown

.. autofunction:: king_phisher.server.server_rpc.rpc_version
