GObject Signals
===============

.. _gobject-signals-application-label:

KingPhisherClientApplication Signals
------------------------------------

The following are the signals for the
:py:class:`~king_phisher.client.application.KingPhisherClientApplication`
object. These signals can be used by the client API to subscribe to specific
events.

.. py:function:: campaign-changed(campaign_id)

   This signal is emitted when campaign attributes are changed. Subscribers to
   this signal can use it to update and refresh information for the modified
   campaign.

   :param str campaign_id: The ID of the campaign whose information was changed.

.. py:function:: campaign-set(campaign_id)

   This signal is emitted when the user sets the current campaign. Subscribers
   to this signal can use it to update and refresh information for the current
   campaign.

   :param str campaign_id: The ID of the new campaign.

.. py:function:: exit()

   This signal is emitted when the client is exiting. Subscribers can use it as
   a chance to clean up and save any remaining data. It is emitted before the
   client is disconnected from the server. At this point the exit operation can
   not be cancelled.

.. py:function:: exit-confirm()

   This signal is emitted when the client has requested that the application
   exit. Subscribers to this signal can use it as a chance to display a warning
   dialog and cancel the operation.

.. py:function:: rpc-cache-clear()

   This signal is emitted to clear the RPC objects cached information.
   Subsequent invocations of RPC cache enabled methods will return fresh
   information from the server.

.. py:function:: server-connected()

   This signal is emitted when the client has connected to the King Phisher
   server. The default handler sets the initial campaign optionally prompting
   the user to select one if one has not already been selected.
