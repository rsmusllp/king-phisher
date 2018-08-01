GObject Signals
===============

These signals can be used by the client API and plugins to subscribe to
specific events. To explicitly connect after the default handler for a signal,
use the *connect_after* method instead of *connect*. Some signals require a
value to be returned by their handlers as noted.

.. _gobject-signals-application-label:

Signal Flags
------------

The "Signal flags" attribute of each of the signals describes certain attributes
of their respective signals. See the `GObject Signals`_ documentation for more
information including a detailed description of the signal emission process.

:SIGNAL_ACTION:
   Signals with the ``SIGNAL_ACTION`` flag are safe to be emitted from arbitrary
   components within the application. These signals have default handlers which
   perform their action and are not stateful.

:SIGNAL_RUN_FIRST:
   Signals with the ``SIGNAL_RUN_FIRST`` flag execute the default handler before
   handlers which are connected with either the
   :py:meth:`~GObject.Object.connect` or
   :py:meth:`~GObject.Object.connect_after` methods. These signals therefor do
   not provide connected handlers with an opportunity to block the emission of
   the signal from the default handler.

:SIGNAL_RUN_LAST:
   Signals with the ``SIGNAL_RUN_LAST`` flag execute the default function after
   handlers which are connected with the :py:meth:`~GObject.Object.connect`
   method but before handlers which are connected with the
   :py:meth:`~GObject.Object.connect_after` method. This provides connected
   handlers with an opportunity to block the default function by halting
   emissionof the signal by using the
   :py:meth:`~GObject.Object.emit_stop_by_name` method.

.. note::
   Plugins which connect to signals should use the
   :py:meth:`~king_phisher.client.plugins.ClientPlugin.signal_connect` method
   which by defaults uses :py:meth:`~GObject.Object.connect` to connect the
   signal. Alternatively :py:meth:`~GObject.Object.connect_after` can be used by
   setting the **after** keyword argument to ``True``.

Application Signals
-------------------

The following are the signals for the
:py:class:`~king_phisher.client.application.KingPhisherClientApplication`
object.

.. gobject-signal:: campaign-changed(campaign_id)

   This signal is emitted when campaign attributes are changed. Subscribers to
   this signal can use it to update and refresh information for the modified
   campaign.

   :flags: ``SIGNAL_RUN_FIRST``
   :param str campaign_id: The ID of the campaign whose information was changed.

.. gobject-signal:: campaign-created(campaign_id)

   This signal is emitted after the user creates a new campaign id. Subscribers
   to this signal can use it to conduct an action after a new campaign id is created.

   :flags: ``SIGNAL_RUN_FIRST``
   :param str campaign_id: The ID of the new campaign.

.. gobject-signal:: campaign-delete(campaign_id)

   This signal is emitted when the user deletes a campaign. Subscribers
   to this signal can use it to conduct an action after the campaign is deleted.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param str campaign_id: The ID of the campaign.

.. gobject-signal:: campaign-set(old_campaign_id, new_campaign_id)

   This signal is emitted when the user sets the current campaign. Subscribers
   to this signal can use it to update and refresh information for the current
   campaign. The :py:attr:`~KingPhisherClientApplication.config` "campaign_id"
   and "campaign_name" keys have already been updated with the new values when
   this signal is emitted.

   :flags: ``SIGNAL_RUN_FIRST``
   :param str old_campaign_id: The ID of the old campaign or None if the client is selecting one for the first time.
   :param str new_campaign_id: The ID of the new campaign.

.. gobject-signal:: config-load(load_defaults)

   This signal is emitted when the client configuration is loaded from disk. This
   loads all of the clients settings used within the GUI.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param bool load_defaults: Load missing options from the template configuration file.

.. gobject-signal:: config-save()

   This signal is emitted when the client configuration is written to disk. This
   saves all of the settings used within the GUI so they can be restored at a
   later point in time.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. gobject-signal:: credential-delete(row_ids)

   This signal is emitted when the user deletes a credential entry. Subscribers
   to this signal can use it to conduct an action an entry is deleted.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param row_ids: The row IDs that are to be deleted.
   :type row_ids: [int, ...]

.. gobject-signal:: exit()

   This signal is emitted when the client is exiting. Subscribers can use it as
   a chance to clean up and save any remaining data. It is emitted before the
   client is disconnected from the server. At this point the exit operation can
   not be cancelled.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. gobject-signal:: exit-confirm()

   This signal is emitted when the client has requested that the application
   exit. Subscribers to this signal can use it as a chance to display a warning
   dialog and cancel the operation.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. gobject-signal:: message-delete(row_ids)

   This signal is emitted when the user deletes a message entry. Subscribers
   to this signal can use it to conduct an action an entry is deleted.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param row_ids: The row IDs that are to be deleted.
   :type row_ids: [str, ...]

.. gobject-signal:: message-sent(target_uid, target_email)

   This signal is emitted when the user sends a message. Subscribers
   to this signal can use it to conduct an action after the message is sent,
   and the information saved to the database.

   :flags: ``SIGNAL_RUN_FIRST``
   :param str target_uid: Message uid that was sent.
   :param str target_email: Email address associated with the sent message.

.. gobject-signal:: reload-css-style()

   This signal is emitted to reload the style resources of the King Phisher
   client.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. gobject-signal:: rpc-cache-clear()

   This signal is emitted to clear the RPC objects cached information.
   Subsequent invocations of RPC cache enabled methods will return fresh
   information from the server.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. gobject-signal:: server-connected()

   This signal is emitted when the client has connected to the King Phisher
   server. The default handler sets the initial campaign optionally prompting
   the user to select one if one has not already been selected.

   :flags: ``SIGNAL_RUN_FIRST``

.. gobject-signal:: server-disconnected()

   This signal is emitted when the client has disconnected from the King Phisher
   server.

   :flags: ``SIGNAL_RUN_FIRST``

.. gobject-signal:: sftp-client-start()

   This signal is emitted when the client starts sftp client from within
   King Phisher. Subscribers can conduct an action prior to the default option
   being ran from the client configuration.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``

.. gobject-signal:: visit-delete(row_ids)

   This signal is emitted when the user deletes a visit entry. Subscribers
   to this signal can use it to conduct an action an entry is deleted.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param row_ids: The row IDs that are to be deleted.
   :type row_ids: [str, ...]

.. gobject-signal:: unhandled-exception(exc_info, error_uid)

   This signal is emitted when the application encounters an unhandled Python
   exception.

   :flags: ``SIGNAL_RUN_FIRST``
   :param tuple exc_info: A tuple of three objects corresponding to the return value of the :py:func:`sys.exc_info` function representing the exception that was raised.
   :param error_uid: The unique identifier that has been assigned to this exception for tracking.
   :type error_uid: :py:class:`uuid.UUID`

.. _gobject-signals-mail-tab-label:

Mail Tab Signals
----------------

The following are the signals for the
:py:class:`~king_phisher.client.tabs.mail.MailSenderTab` object.

.. gobject-signal:: message-create(target, message)

   This signal is emitted when the message and target have been loaded and
   constructed. Subscribers to this signal may use it as an opportunity to
   modify the message object prior to it being sent.

   .. versionadded:: 1.10.0b3

   :flags: ``SIGNAL_RUN_FIRST``
   :param target: The target for the message.
   :type target: :py:class:`~king_phisher.client.mailer.MessageTarget`
   :param message: The message about to be sent to the target.
   :type message: :py:class:`~king_phisher.client.mailer.TopMIMEMultipart`

.. gobject-signal:: message-data-export(target_file)

   This signal is emitted when the client is going to export the message
   configuration to a King Phisher Message (KPM) archive file.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param str target_file: The path to write the archive file to.
   :return: Whether or not the message archive was successfully imported.
   :rtype: bool

.. gobject-signal:: message-data-import(target_file, dest_dir)

   This signal is emitted when the client is going to import the message
   configuration from a King Phisher Message (KPM) archive file.

   :flags: ``SIGNAL_ACTION | SIGNAL_RUN_LAST``
   :param str target_file: The source archive file to import.
   :param str dest_dir: The destination directory to unpack the archive into.
   :return: Whether or not the message archive was successfully imported.
   :rtype: bool

.. gobject-signal:: message-send(target, message)

   This signal is emitted after the message has been fully constructed
   (after :gsig:`message-create`) and can be used as an opportunity to
   inspect the message object and prevent it from being sent.

   .. versionadded:: 1.10.0b3

   :flags: ``SIGNAL_RUN_LAST``
   :param target: The target for the message.
   :type target: :py:class:`~king_phisher.client.mailer.MessageTarget`
   :param message: The message about to be sent to the target.
   :type message: :py:class:`~king_phisher.client.mailer.TopMIMEMultipart`
   :return: Whether or not to proceed with sending the message.
   :rtype: bool

.. gobject-signal:: send-finished()

   This signal is emitted after all messages have been sent.

   :flags: ``SIGNAL_RUN_FIRST``

.. gobject-signal:: send-precheck()

   This signal is emitted when the user is about to start sending phishing
   messages. It is used to ensure that all settings are sufficient before
   proceeding. A handler can return False to indicate that a pre-check condition
   has failed and the operation should be aborted.

   :flags: ``SIGNAL_RUN_LAST``
   :return: Whether or not the handler's pre-check condition has passed.
   :rtype: bool

.. gobject-signal:: target-create(target)

   This signal is emitted when the target has been loaded and constructed.
   Subscribers to this signal may use it as an opportunity to modify the
   target object prior to it being sent.

   .. versionadded:: 1.10.0b3

   :flags: ``SIGNAL_RUN_FIRST``
   :param target: The target for the message.
   :type target: :py:class:`~king_phisher.client.mailer.MessageTarget`

.. gobject-signal:: target-send(target)

   This signal is emitted after the target has been fully constructed (after
   :gsig:`target-create`) and can be used as an opportunity to inspect
   the target object and prevent it from being sent to.

   .. versionadded:: 1.10.0b3

   :flags: ``SIGNAL_RUN_LAST``
   :param target: The target for the message.
   :type target: :py:class:`~king_phisher.client.mailer.MessageTarget`
   :return: Whether or not to proceed with sending to the target.
   :rtype: bool

Server Event Signals
--------------------

The following are the signals for the
:py:class:`~king_phisher.client.server_events.ServerEventSubscriber` object.
These events are published by the server forwarded to the client based on the
active subscriptions. When an event is forwarded to a client the corresponding
GObject signal is emitted for consumption by the client. See the section on
:ref:`server-published-events-label` for more details.

.. gobject-signal:: db-alert-subscriptions(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-campaigns(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-campaign-types(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-companies(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-company-departments(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-credentials(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-deaddrop-connections(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-deaddrop-deployments(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-industries(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-landing-pages(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-messages(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-users(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. gobject-signal:: db-visits(event_type, objects)

   :flags: ``SIGNAL_RUN_FIRST``
   :param str event_type: The type of event, one of either deleted, inserted or updated.
   :param list objects: The objects from the server. The available attributes depend on the subscription.

.. _GObject Signals: https://developer.gnome.org/gobject/stable/signal.html
