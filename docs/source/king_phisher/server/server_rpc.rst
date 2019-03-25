:mod:`server_rpc`
=================

.. module:: king_phisher.server.server_rpc
   :synopsis:

This module provides the RPC server functionality that is used by the client
to communicate with the server application.

Data
----

.. autodata:: CONFIG_READABLE
   :annotation:

.. autodata:: CONFIG_WRITEABLE
   :annotation:

.. autodata:: RPC_AUTH_HEADER

.. autodata:: VIEW_ROW_COUNT

Functions
---------

.. autofunction:: register_rpc

.. autofunction:: rpc_campaign_alerts_is_subscribed

.. autofunction:: rpc_campaign_alerts_subscribe

.. autofunction:: rpc_campaign_alerts_unsubscribe

.. autofunction:: rpc_campaign_landing_page_new

.. autofunction:: rpc_campaign_message_new

.. autofunction:: rpc_campaign_new

.. autofunction:: rpc_campaign_stats

.. autofunction:: rpc_config_get

.. autofunction:: rpc_config_set

.. autofunction:: rpc_events_is_subscribed

.. autofunction:: rpc_events_subscribe

.. autofunction:: rpc_events_unsubscribe

.. autofunction:: rpc_database_count_rows

.. autofunction:: rpc_database_delete_row_by_id

.. autofunction:: rpc_database_delete_rows_by_id

.. autofunction:: rpc_database_get_row_by_id

.. autofunction:: rpc_database_insert_row

.. autofunction:: rpc_database_set_row_value

.. autofunction:: rpc_database_view_rows

.. autofunction:: rpc_geoip_lookup

.. autofunction:: rpc_geoip_lookup_multi

.. autofunction:: rpc_graphql

.. autofunction:: rpc_hostnames_add

.. autofunction:: rpc_hostnames_get

.. autofunction:: rpc_login

.. autofunction:: rpc_logout

.. autofunction:: rpc_ping

.. autofunction:: rpc_plugins_list

.. autofunction:: rpc_shutdown

.. autofunction:: rpc_ssl_hostnames_get

.. autofunction:: rpc_ssl_hostnames_load

.. autofunction:: rpc_ssl_hostnames_unload

.. autofunction:: rpc_ssl_letsencrypt_issue

.. autofunction:: rpc_ssl_letsencrypt_certbot_version

.. autofunction:: rpc_ssl_status

.. autofunction:: rpc_version
