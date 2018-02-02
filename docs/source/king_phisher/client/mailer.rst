:mod:`mailer`
=============

.. module:: king_phisher.client.mailer
   :synopsis:

This module provides the functionality used to create and sending messages from
the client application.

Functions
---------

.. autofunction:: guess_smtp_server_address

.. autofunction:: render_message_template

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
