GObject Signals
===============

.. _gobject-signals-application-label:

KingPhisherClientApplication Signals
------------------------------------

.. py:function:: campaign-set(campaign_id)

   This signal is emitted when the user sets the current campaign. Subscribers
   to this signal can use it to update and refresh information for the current
   campaign.

   :object: :py:class:`~king_phisher.client.application.KingPhisherClientApplication`
   :param str campaign_id: The ID of the new campaign.

.. py:function:: server-connected()

   This signal is emitted with the client has connected to the King Phisher
   Server. The default handler sets the initial campaign optionally prompting
   the user to select one if one has not already been selected.

   :object: :py:class:`~king_phisher.client.application.KingPhisherClientApplication`


.. _gobject-signals-window-label:

KingPhisherClient Signals
-------------------------

.. py:function:: exit()

   This signal is emitted when the client is exiting. Subscribers can use it as
   a chance to clean up and save any remaining data. It is emitted before the
   client is disconnected from the server. At this point the exit operation can
   not be cancelled.

   :object: :py:class:`~king_phisher.client.client.KingPhisherClient`

.. py:function:: exit-confirm()

   This signal is emitted when the client has requested that the application
   exit. Subscribers to this signal can use it as a chance to display a warning
   dialog and cancel the operation.

   :object: :py:class:`~king_phisher.client.client.KingPhisherClient`
