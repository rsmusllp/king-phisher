Server Plugins
==============

Server plugins need to inherit from the
:py:class:`~king_phisher.server.plugins.ServerPlugin` class which provides the
basic outline. Server plugins have access to their respective configurations
from the :py:attr:`~king_phisher.server.plugins.ServerPlugin.config` attribute.
This configuration can be changed at runtime, but changes will not be kept after
the server has stopped.
