Schema
======

.. gql:object:: GeoLocation

   Location information as retrieved for an arbitrary IP address.

   .. gql:field:: city

      :type: String

      The city in which the location resides.

   .. gql:field:: continent

      :type: String

      The continent in which the location resides.

   .. gql:field:: coordinates

      :type: [Float]

      The coordinates of the location as an array of floating point numbers
      containing the latitude and longitude.

   .. gql:field:: country

      :type: String

      The country in which the location resides.

   .. gql:field:: postalCode

      :type: String

      The postal code in which the location resides.

   .. gql:field:: timeZone

      :type: String

      The time zone in which the location resides.

.. gql:object:: Plugin

   Information regarding a server plugin.

   .. gql:field:: authors

      :type: [String]

      A list containing each of the author names.

   .. gql:field:: classifiers

      :type: [String]

      A list of string classifiers for describing qualities.

   .. gql:field:: description

      :type: String

      A text description of the plugin including what it does and any other
      information that may be necessary for users to know.

   .. gql:field:: homepage

      :type: String

      A URL for the homepage where the plugin originated.

   .. gql:field:: name

      :type: String

      The name of the plugin. As opposed to :gql:fld:`~Plugin.title`, this value
      is an internal identifier derived from the plugin's file name and should
      not change.

   .. gql:field:: reference_urls

      :type: [String]

      An optional list of URLs to use as references.

   .. gql:field:: title

      :type: String

      The plaintext title of the plugin to display in the UI. Unlike
      :gql:fld:`~Plugin.name`, this value is intended for human consumption and
      may be updated.

   .. gql:field:: version

      :type: String

      The version of the template data.

.. gql:object:: SiteTemplate

   Information for a site template which is available for use on the server. The
   template information can be used by the client to build a pretext and
   determine a landing page URL. As opposed to the
   :gql:obj:`SiteTemplateMetadata` object, this structure contains information
   regarding where the template is installed versus what the template is.

   .. gql:field:: created

      :type: DateTime

      The timestamp of when this site template was created.

   .. gql:field:: hostname

      :type: String

      An optional hostname associated with this site template. This setting is
      only applicable when VHOSTs are enabled.

   .. gql:field:: path

      :type: String

      The path at which the site template is installed relative to the web root.
      This value must be used as the root for the pages defined in the metadata.

   .. gql:field:: metadata

      :type: :gql:obj:`SiteTemplateMetadata`

      Metadata describing the site template.

.. gql:object:: SiteTemplateMetadata

   Metadata for a specific site template describing what it is. As opposed to
   the :gql:obj:`SiteTemplate` object, this structure contains information on
   what the template is versus where it is installed.

   .. gql:field:: authors

      :type: [String]

      A list containing each of the author names.

   .. gql:field:: classifiers

      :type: [String]

      A list of string classifiers for describing qualities.

   .. gql:field:: description

      :type: String

      A text description for the template, containing any notes for the user.

   .. gql:field:: homepage

      :type: String

      A URL for the homepage where the template originated.

   .. gql:field:: pages

      :type: [String]

      A list of relative paths suitable for use as landing pages

   .. gql:field:: referenceUrls

      :type: [String]

      A list of reference URL strings for the template.

   .. gql:field:: title

      :type: String

      The template's title.

   .. gql:field:: version

      :type: String

      The version of the template data.

.. gql:object:: SSL

   Information regarding the use, configuration and capabilities of SSL on the
   server.

   .. gql:field:: sniHostname(hostname: String!)

      :param String! hostname: The hostname to retrieve the SNI configuration
         for.
      :type: :gql:obj:`SNIHostname`

      A field for looking up the SNI configuration for a specific hostname.

   .. gql:field:: sniHostnames

      :type: Connection

      A connection for enumerating all of the available SNI configurations.

   .. gql:field:: status

      :type: :gql:obj:`SSLStatus`

      An object describing the status of the server's SSL configuration.

.. gql:object:: SNIHostname

   An object describing the configuration of SSL's Server Name Indicator (SNI)
   extension for a specific hostname. If this object exists, the necessary data
   files are available however they may or may not be loaded as indicated by the
   :gql:fld:`~SNIHostname.enabled` field.

   .. gql:field:: enabled

      :type: Boolean

      Whether or not the hostname is enabled.

   .. gql:field:: hostname

      :type: String

      The hostname for this configuration.

.. gql:object:: SSLStatus

   An object describing the status of SSL as used by the server.

   .. gql:field:: enabled

      :type: Boolean

      Whether or not SSL is enabled for any interface the server is bound with.

   .. gql:field:: hasSni

      :type: Boolean

      Whether or not SSL's Server Name Indicator (SNI) extension is available in
      the Python implementation.
