:mod:`pam` --- PAM module for Python
====================================

.. module:: pam
   :synopsis: PAM module for Python

This module provides an authenticate function that will allow the caller to
authenticate a user against the Pluggable Authentication Modules (PAM) on the
system.

.. py:function:: authenticate(username, password, service='login')

   Returns True if the given username and password authenticate for the given
   service.

   :param str username: The username to test authenticate with.
   :param str password: The password in plain text to test authentication with.
   :param str service: The PAM service to authenticate against.
   :return: The status of the authentication attempt is returned.
   :rtype: bool
