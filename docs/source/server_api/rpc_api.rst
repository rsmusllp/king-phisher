.. _rpc-api-label:

RPC API
=======

Overview
--------

The RPC API is used by the King Phisher client to communicate with the server.
It uses the RPC capabilities provided by the
:py:mod:`~king_phisher.third_party.AdvancedHTTPServer` module for the
underlying communications. The RPC API provides a way for the client to
retrieve and set information regarding campaigns as well as the server's
configuration. RPC requests must be authenticated and are only permitted from
the loopback interface. The client is responsible for using SSH to set up a port
forward for requests.

.. _rpc-api-general-api-label:

General API
-----------

.. rpc:function:: client/initialize()

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_client_initialize`

.. rpc:function:: ping()

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_ping`

.. rpc:function:: shutdown()

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_shutdown`

.. rpc:function:: version()

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_version`

.. _rpc-api-campaign-api-label:

Campaign API
------------

.. rpc:function:: campaign/alerts/is_subscribed(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_alerts_is_subscribed`

.. rpc:function:: campaign/alerts/subscribe(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_alerts_subscribe`

.. rpc:function:: campaign/alerts/unsubscribe(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_alerts_unsubscribe`

.. rpc:function:: campaign/landing_page/new(campaign_id, hostname, page)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_landing_page_new`

.. rpc:function:: campaign/message/new(campaign_id, email_id, email_target, company_name, first_name, last_name)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_message_new`

.. rpc:function:: campaign/new(name)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_new`

.. _rpc-api-campaign-table-api-label:

Campaign Table API
^^^^^^^^^^^^^^^^^^

.. rpc:function:: campaign/(str:table_name)/count(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. rpc:function:: campaign/(str:table_name)/view(campaign_id, page=0)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_view_rows`

.. _rpc-api-configuration-api-label:

Configuration API
-----------------

.. rpc:function:: config/get(option_name)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_config_get`

.. rpc:function:: config/set(options)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_config_set`

.. _rpc-api-geoip-api-label:

GeoIP API
---------

.. rpc:function:: geoip/lookup(ip, lang=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_geoip_lookup`

.. rpc:function:: geoip/lookup/multi(ips, lang=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_geoip_lookup_multi`

.. _rpc-api-message-api-label:

Message API
-----------

.. rpc:function:: message/credentials/count(message_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. rpc:function:: message/credentials/view(message_id, page=0)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_view_rows`

.. rpc:function:: message/visits/count(message_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. rpc:function:: message/visits/view(message_id, page=0)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_view_rows`

.. _rpc-api-table-api-label:

Table API
---------

.. rpc:function:: (str:table_name)/count()

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. rpc:function:: (str:table_name)/delete(row_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_delete_row_by_id`

.. rpc:function:: (str:table_name)/delete/multi(row_ids)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_delete_rows_by_id`

.. rpc:function:: (str:table_name)/get(row_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_get_row_by_id`

.. rpc:function:: (str:table_name)/insert(keys, values)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_insert_row`

.. rpc:function:: (str:table_name)/set(row_id, keys, values)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_set_row_value`

.. rpc:function:: (str:table_name)/view(page=0)

   :handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_view_rows`
