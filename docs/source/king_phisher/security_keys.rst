:mod:`security_keys`
====================

.. module:: king_phisher.security_keys
   :synopsis:

This module provides functionality for working with security keys that are
used for data integrity checks. Verification is performed using ECDSA keys.

Data
----

.. autodata:: ecdsa_curves
   :annotation:

Functions
---------

.. autofunction:: openssl_decrypt_data

.. autofunction:: openssl_derive_key_and_iv

Classes
-------

.. autoclass:: SecurityKeys
   :show-inheritance:
   :members:
   :inherited-members:
   :special-members: __init__

.. autoclass:: SigningKey
   :show-inheritance:
   :members:

.. autoclass:: VerifyingKey
   :show-inheritance:
   :members:
