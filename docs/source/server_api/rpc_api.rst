.. _rpc-api-label:

RPC API
=======

Overview
--------

The RPC API is used by the King Phisher client to communicate with the server.
It uses the RPC capabilities provided by the
:py:mod:`AdvancedHTTPServer` module for the underlying communications. The RPC
API provides a way for the client to retrieve and set information regarding
campaigns as well as the server's configuration. RPC requests must be
authenticated and are only permitted from the loopback interface. The client is
responsible for using SSH to set up a port forward for requests.

.. _rpc-api-general-api-label:

General API
-----------

.. rpc:function:: login()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_login`

.. rpc:function:: logout()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_logout`

.. rpc:function:: ping()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_ping`

.. rpc:function:: plugins/list()

   :handler: :py:func:`~kking_phisher.server.server_rpc.rpc_plugins_list`

.. rpc:function:: shutdown()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_shutdown`

.. rpc:function:: version()

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_version`

.. _rpc-api-campaign-api-label:

Campaign API
------------

.. rpc:function:: campaign/alerts/is_subscribed(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_alerts_is_subscribed`

.. rpc:function:: campaign/alerts/subscribe(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_alerts_subscribe`

.. rpc:function:: campaign/alerts/unsubscribe(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_alerts_unsubscribe`

.. rpc:function:: campaign/landing_page/new(campaign_id, hostname, page)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_landing_page_new`

.. rpc:function:: campaign/message/new(campaign_id, email_id, email_target, company_name, first_name, last_name)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_message_new`

.. rpc:function:: campaign/new(name, description=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_new`

.. rpc:function:: campaign/stats(campaign_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_campaign_stats`

.. _rpc-api-configuration-api-label:

Configuration API
-----------------

.. rpc:function:: config/get(option_name)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_config_get`

.. rpc:function:: config/set(options)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_config_set`

.. _rpc-api-geoip-api-label:

GeoIP API
---------

.. rpc:function:: geoip/lookup(ip, lang=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_geoip_lookup`

.. rpc:function:: geoip/lookup/multi(ips, lang=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_geoip_lookup_multi`

.. _rpc-api-table-api-label:

Table API
---------

.. rpc:function:: db/table/count(table_name, query_filter=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_count_rows`

.. rpc:function:: db/table/delete(table_name, row_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_delete_row_by_id`

.. rpc:function:: db/table/delete/multi(table_name, row_ids)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_delete_rows_by_id`

.. rpc:function:: db/table/get(table_name, row_id)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_get_row_by_id`

.. rpc:function:: db/table/insert(table_name, keys, values)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_insert_row`

.. rpc:function:: db/table/set(table_name, row_id, keys, values)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_set_row_value`

.. rpc:function:: db/table/view(table_name, page=0, query_filter=None)

   :handler: :py:func:`~king_phisher.server.server_rpc.rpc_database_view_rows`
