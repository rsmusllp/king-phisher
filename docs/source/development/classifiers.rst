Classifiers
===========

Classifier strings can be applied to complex objects to describe arbitrary
qualities that are desirable to determine pragmatically. For example, a
classifier can be used to describe that a client plugin is intended to be used
for Spam evasion purposes or that a server template is intended to be used for
gathering credentials. Data structures which use classifiers expose them as a
list of strings to allow for multiple classifiers to be defined. When defining a
classifier, it is important that the classifier is not unique as the purpose of
the data is to identify objects by arbitrary traits.

Classifier Format
-----------------

Classifiers take a simple format of one or more words separated by two colons
(``::``). The words should be capitalized for consistency and are arranged in a
hierarchical format. For example, ``Foo :: Bar :: Baz`` overlaps with
``Foo :: Bar`` and thus an object with the ``Foo :: Bar :: Baz`` classifier
implicitly contains ``Foo :: Bar`` and does not require it to be explicitly
defined. As such, while searching classifiers, a query term of ``Foo :: Bar``
must match ``Foo :: Bar :: Baz``.

Common Classifiers
------------------

The following is a reference of common classifiers, mostly used by external
components such as plugins and templates.

**Plugin :: Client** -- An executable plugin to be loaded by the King Phisher
client that will typically provide new or modify existing functionality.

**Plugin :: Client :: Email :: Attachment** -- A client plugin which creates or
modifies email attachments.

**Plugin :: Client :: Email :: Spam Evasion** -- A client plugin which can be
used for the purpose of Spam filter evasion.

**Plugin :: Client :: Tool** - A client plugin which provides generic utility
functionality typically for the purposes of convenience.

**Plugin :: Client :: Tool :: Data Management** -- A client plugin which manages
data in some fashion such as for organization or archival purposes.

**Plugin :: Server** -- An executable plugin to be loaded by the King Phisher
server that will typically provide new or modify existing functionality.

**Plugin :: Server :: Notifications** -- A server plugin which dispatches
notifications through an arbitrary, plugin-provided means.

**Plugin :: Server :: Notifications :: Alerts** -- A server plugin which
dispatches notifications through the alerts interface. Notifications through the
alerts interface can be self-managed by individual users as opposed to being
server-wide.

**Script :: CLI** -- An object, typically a plugin which  provides an interface
to be executed as a standalone script from the command line.

**Template :: Site** -- A template for use by the King Phisher server to be
presented to targeted users when they visit. When used as parting of a phishing
campaign, a site template provides the content to be viewed by users which have
fallen for the pretext.

**Template :: Site :: Credentials** -- A site template which incorporates
functionality for prompt the visitor for and recording submitted credentials.

**Template :: Site :: Payload** -- A site template which will provide the
visitor with a payload of some kind (typically an executable file) with the
intention of having them run it.

**Template :: Site :: Training** -- A site template that informs the user that
they were involved in a phishing exercise, failed and attempts provide
information for training purposes.
