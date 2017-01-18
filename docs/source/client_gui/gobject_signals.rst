GObject Signals
===============

These signals can be used by the client API and plugins to subscribe to
specific events. To explicitly connect after the default handler for a signal,
use the *connect_after* method instead of *connect*. Some signals require a
value to be returned by their handlers as noted.

.. _gobject-signals-application-label:

Application Signals
-------------------

The following are the signals for the
:py:class:`~king_phisher.client.application.KingPhisherClientApplication`
object.

.. py:function:: campaign-changed(campaign_id)

   This signal is emitted when campaign attributes are changed. Subscribers to
   this signal can use it to update and refresh information for the modified
   campaign.

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str campaign_id: The ID of the campaign whose information was changed.

.. py:function:: campaign-created(campaign_id)

   This signal is emitted after the user creates a new campaign id. Subscribers
   to this signal can use it to conduct an action after a new campaign id is created.

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str campaign_id: The ID of the new campaign.

.. py:function:: campaign-delete(campaign_id)

   This signal is emitted when the user deletes a campaign. Subscribers
   to this signal can use it to conduct an action after the campaign is deleted.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param str campaign_id: The ID of the campaign.

.. py:function:: campaign-set(campaign_id)

   This signal is emitted when the user sets the current campaign. Subscribers
   to this signal can use it to update and refresh information for the current
   campaign.

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str campaign_id: The ID of the campaign.

.. py:function:: config-load(load_defaults)

   This signal is emitted when the client configuration is loaded from disk. This
   loads all of the clients settings used within the GUI.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param bool load_defaults: Load missing options from the template configuration file.

.. py:function:: config-save()

   This signal is emitted when the client configuration is written to disk. This
   saves all of the settings used within the GUI so they can be restored at a
   later point in time.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. py:function:: credential-delete(row_ids)

   This signal is emitted when the user deletes a credential entry. Subscribers
   to this signal can use it to conduct an action an entry is deleted.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param row_ids: The row IDs that are to be deleted.
   :type row_ids: [int, ...]

.. py:function:: exit()

   This signal is emitted when the client is exiting. Subscribers can use it as
   a chance to clean up and save any remaining data. It is emitted before the
   client is disconnected from the server. At this point the exit operation can
   not be cancelled.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. py:function:: exit-confirm()

   This signal is emitted when the client has requested that the application
   exit. Subscribers to this signal can use it as a chance to display a warning
   dialog and cancel the operation.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. py:function:: message-delete(row_ids)

   This signal is emitted when the user deletes a message entry. Subscribers
   to this signal can use it to conduct an action an entry is deleted.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param row_ids: The row IDs that are to be deleted.
   :type row_ids: [str, ...]

.. py:function:: message-sent(target_uid, target_email)

   This signal is emitted when the user sends a message. Subscribers
   to this signal can use it to conduct an action after the message is sent,
   and the information saved to the database.

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str target_uid: Message uid that was sent.
   :param str target_email: Email address associated with the sent message.

.. py:function:: reload-css-style()

   This signal is emitted to reload the style resources of the King Phisher
   client.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. py:function:: rpc-cache-clear()

   This signal is emitted to clear the RPC objects cached information.
   Subsequent invocations of RPC cache enabled methods will return fresh
   information from the server.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. py:function:: server-connected()

   This signal is emitted when the client has connected to the King Phisher
   server. The default handler sets the initial campaign optionally prompting
   the user to select one if one has not already been selected.

   :signal flags: ``SIGNAL_RUN_FIRST``

.. py:function:: server-disconnected()

   This signal is emitted when the client has disconnected from the King Phisher
   server.

   :signal flags: ``SIGNAL_RUN_FIRST``

.. py:function:: sftp-client-start()

   This signal is emitted when the client starts sftp client from within
   King Phisher. Subscribers can conduct an action prior to the default option
   being ran from the client configuration.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. py:function:: visit-delete(row_ids)

   This signal is emitted when the user deletes a visit entry. Subscribers
   to this signal can use it to conduct an action an entry is deleted.

   :signal flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param row_ids: The row IDs that are to be deleted.
   :type row_ids: [str, ...]

.. py:function:: unhandled-exception(exc_info, error_uid)

   This signal is emitted when the application encounters an unhandled Python
   exception.

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param tuple exc_info: A tuple of three objects corresponding to the return value of the :py:func:`sys.exc_info` function representing the exception that was raised.
   :param error_uid: The unique identifier that has been assigned to this exception for tracking.
   :type error_uid: :py:class:`uuid.UUID`

Mail Tab Signals
----------------

The following are the signals for the
:py:class:`~king_phisher.client.tabs.mail.MailSenderTab` object.

.. py:function:: send-finished()

   This signal is emitted after all messages have been sent.

   :signal flags: ``SIGNAL_RUN_FIRST``

.. py:function:: send-precheck()

   This signal is emitted when the user is about to start sending phishing
   messages. It is used to ensure that all settings are sufficient before
   proceeding. A handler can return False to indicate that a pre-check condition
   has failed and the operation should be aborted.

   :signal flags: ``SIGNAL_RUN_LAST``
   :return: Whether or not the handler's pre-check condition has passed.
   :rtype: bool

.. py:function:: send-target(target)

   This signal is emitted when the target for a message has been loaded.
   Subscribers to this signal can use it as an opportunity to modify the
   target's attributes, including but not limited to the email address.

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param target: The target for the message.
   :type target: :py:class:`~king_phisher.client.mailer.MessageTarget`

Server Event Signals
--------------------

The following are the signals for the
:py:class:`~king_phisher.client.server_events.ServerEventSubscriber` object.
These events are published by the server forwarded to the client based on the
active subscriptions. When an event is forwarded to a client the corresponding
GObject signal is emitted for consumption by the client. See the section on
:ref:`server-published-events-label` for more details.

.. py:function:: db-alert-subscriptions(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-campaigns(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-campaign-types(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-companies(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-company-departments(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-credentials(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-deaddrop-connections(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-deaddrop-deployments(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-industries(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-landing-pages(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-messages(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-users(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. py:function:: db-visits(event_type, objects)

   :signal flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.
