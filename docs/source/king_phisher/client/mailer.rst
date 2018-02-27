:mod:`mailer`
=============

.. module:: king_phisher.client.mailer
   :synopsis:

This module provides the functionality used to create and sending messages from
the client application.

Data
----

.. autodata:: MIME_TEXT_PLAIN

Functions
---------

.. autofunction:: count_targets_file

.. autofunction:: get_invite_start_from_config

.. autofunction:: guess_smtp_server_address

.. autofunction:: render_message_template

.. autofunction:: rfc2282_timestamp

Classes
-------

.. autoclass:: MailSenderThread
   :show-inheritance:
   :members:
   :special-members: __init__

.. autoclass:: MessageAttachments
   :members:

.. autoclass:: MessageTarget
   :members:

.. autoclass:: TopMIMEMultipart
   :show-inheritance:
   :members:
   :special-members: __init__
