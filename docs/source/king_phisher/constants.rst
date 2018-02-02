:mod:`constants`
================

.. module:: king_phisher.constants
   :synopsis:

This module keeps collections of related constants organized for use in other
modules.

Data
----

.. autodata:: DEFAULT_LOG_LEVEL

.. autodata:: DISABLED

Classes
-------

.. autoclass:: ConstantGroup
   :members:
   :undoc-members:

.. autoclass:: ConnectionErrorReason
.. autoattribute:: ConnectionErrorReason.ERROR_AUTHENTICATION_FAILED
.. autoattribute:: ConnectionErrorReason.ERROR_CONNECTION
.. autoattribute:: ConnectionErrorReason.ERROR_INCOMPATIBLE_VERSIONS
.. autoattribute:: ConnectionErrorReason.ERROR_INVALID_CREDENTIALS
.. autoattribute:: ConnectionErrorReason.ERROR_INVALID_OTP
.. autoattribute:: ConnectionErrorReason.ERROR_PORT_FORWARD
.. autoattribute:: ConnectionErrorReason.ERROR_UNKNOWN
.. autoattribute:: ConnectionErrorReason.SUCCESS

.. autoclass:: OSArch
.. autoattribute:: OSArch.PPC
.. autoattribute:: OSArch.X86
.. autoattribute:: OSArch.X86_64

.. autoclass:: OSFamily
.. autoattribute:: OSFamily.ANDROID
.. autoattribute:: OSFamily.BLACKBERRY
.. autoattribute:: OSFamily.IOS
.. autoattribute:: OSFamily.LINUX
.. autoattribute:: OSFamily.OSX
.. autoattribute:: OSFamily.WINDOWS
