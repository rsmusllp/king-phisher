.. _rpc-api-label:

RPC API
=======

.. py:function:: client/initialize()
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_client_initialize`

.. py:function:: ping()
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_ping`

.. py:function:: shutdown()
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_shutdown`

.. py:function:: version()
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_version`

.. _rpc-api-campaign-api-label:

Campaign API
------------

.. py:function:: campaign/alerts/is_subscribed(campaign_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_alerts_is_subscribed`

.. py:function:: campaign/alerts/subscribe(campaign_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_alerts_subscribe`

.. py:function:: campaign/alerts/unsubscribe(campaign_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_alerts_unsubscribe`

.. py:function:: campaign/delete(campaign_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_delete`

.. py:function:: campaign/landing_page/new(campaign_id, hostname, page)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_landing_page_new`

.. py:function:: campaign/message/new(campaign_id, email_id, email_target, company_name, first_name, last_name)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_message_new`

.. py:function:: campaign/new(name)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_campaign_new`

.. _rpc-api-campaign-table-api-label:

Campaign Table API
^^^^^^^^^^^^^^^^^^

.. py:function:: campaign/(str:table_name)/count(campaign_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. py:function:: campaign/(str:table_name)/view(campaign_id, page=0)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_get_rows`

.. _rpc-api-configuration-api-label:

Configuration API
-----------------

.. py:function:: config/get(option_name)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_config_get`

.. py:function:: config/set(options)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_config_set`

.. _rpc-api-geoip-api-label:

GeoIP API
---------

.. py:function:: geoip/lookup(ip, lang=None)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_geoip_lookup`

.. py:function:: geoip/lookup/multi(ips, lang=None)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_geoip_lookup_multi`

.. _rpc-api-message-api-label:

Message API
-----------

.. py:function:: message/credentials/count(message_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. py:function:: message/credentials/view(message_id, page=0)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_get_rows`

.. py:function:: message/visits/count(message_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. py:function:: message/visits/view(message_id, page=0)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_get_rows`

.. _rpc-api-table-api-label:

Table API
---------

.. py:function:: (str:table_name)/count()
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_count_rows`

.. py:function:: (str:table_name)/delete(row_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_delete_row_by_id`

.. py:function:: (str:table_name)/delete/multi(row_ids)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_delete_rows_by_id`

.. py:function:: (str:table_name)/get(row_id)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_get_row_by_id`

.. py:function:: (str:table_name)/insert(keys, values)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_insert_row`

.. py:function:: (str:table_name)/set(row_id, keys, values)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_set_row_value`

.. py:function:: (str:table_name)/view(page=0)
   :noindex:

   :Handler: :py:func:`~king_phisher.server.server_rpc.KingPhisherRequestHandlerRPC.rpc_database_get_rows`
