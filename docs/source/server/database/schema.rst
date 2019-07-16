.. py:currentmodule:: king_phisher.server.database

.. _database-schema-label:

Database Schema
===============

This schema defines the various database tables and fields for the objects
managed by the King Phisher server. These are exposed over the
:ref:`GraphQL <graphql-label>` interface with the exception of fields which are
restricted based on permissions.

Tables
------

.. db:table:: alert_subscriptions

   Subscriptions to alerts for campaigns that users are interested in receiving
   notifications for.

   .. db:field:: expiration

      The expiration for which the user can set to no longer receive
      notifications.

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: user_id

      The identifier of the user which created the alert subscription.

      :nullable: False
      :foreignkey: :db:fld:`users.id`
            
   .. db:field:: campaign_id

      The identifier of the campaign the user is interested in receiving
      notifications for.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
.. db:table:: authenticated_sessions

   An authenticated session associated with a user that has logged into the
   server over RPC.

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: created

      The time at which the session was created.

      :nullable: False
      :type: DateTime
      
   .. db:field:: last_seen

      The time at which the last authenticated request associated with this
      session was seen. Used to support session timeouts.

      :nullable: False
      :type: DateTime
      
   .. db:field:: user_id

      The identifier of the authenticated user who established this session.

      :nullable: False
      :foreignkey: :db:fld:`users.id`
            
.. db:table:: campaign_types

   The type information for a particular campaign. This information is useful
   for determining the success metrics. For example, a campaign type can be set
   as "Credentials" for a campaign intending to collect credentials from users
   while a campaign which does not can have the type set to "Visits". This will
   ensure that the campaign of type "Visits" is not considered to be less
   successful due to it having not collected any credentials.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      A short name for the campaign type, e.g. "Credentials".

      :nullable: False
      :type: String
      
   .. db:field:: description

      A description of the campaign type, e.g. "Campaigns that intend to collect
      credentials from target users".

      :nullable: True
      :type: String
      
.. db:table:: campaigns

   A logical testing unit representing a single campaign.

   .. db:field:: expiration

      The time at which the server should cease collection of testings
      information.

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      A short, human-readable name for the campaign.

      :nullable: False
      :type: String
      
   .. db:field:: description

      A field to store any descriptive information regarding the campaign such
      as why or how it was conducted.

      :nullable: True
      :type: String
      
   .. db:field:: user_id

      The identifier of the user who originally created the campaign.

      :nullable: False
      :foreignkey: :db:fld:`users.id`
            
   .. db:field:: created

      The time at which the campaign was created.

      :nullable: True
      :type: DateTime
      
   .. db:field:: max_credentials

      The maximum number of credentials to collect *per user*. This setting can
      be used to alter how the server behaves when a target submits multiple
      credentials during the course of a campaign.

      :nullable: True
      :type: Integer
      
   .. db:field:: campaign_type_id

      The identifier for the campaign's type.

      :nullable: True
      :foreignkey: :db:fld:`campaign_types.id`
            
   .. db:field:: company_id

      The identifier for the company for which this campaign performs testing.

      :nullable: True
      :foreignkey: :db:fld:`companies.id`
            
   .. db:field:: credential_regex_username

      A regular expression that can be used to determine the validity of a
      credential's username field.

      :nullable: True
      :type: String
      
   .. db:field:: credential_regex_password

      A regular expression that can be used to determine the validity of a
      credential's password field.

      :nullable: True
      :type: String
      
   .. db:field:: credential_regex_mfa_token

      A regular expression that can be used to determine the validity of a
      credential's mfa token field.

      :nullable: True
      :type: String
      
.. db:table:: companies

   An entity for which a campaign's test is conducted for.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      A short, human-readable name for the entity.

      :nullable: False
      :type: String
      
   .. db:field:: description

      A field to store any descriptive information regarding the entity.

      :nullable: True
      :type: String
      
   .. db:field:: industry_id

      The identifier of the primary industry in which the entity operates.

      :nullable: True
      :foreignkey: :db:fld:`industries.id`

   .. db:field:: url_main

      The URL to the entity's main web site, useful for incorporation into site
      templates.

      :nullable: True
      :type: String
      
   .. db:field:: url_email

      The URL to the entity's email portal, useful for incorporation into site
      templates.


      :nullable: True
      :type: String
      
   .. db:field:: url_remote_access

      The URL for the entity's remote access solution, useful for incorporation
      into site templates.

      :nullable: True
      :type: String
      
.. db:table:: company_departments

   A subdivision of a company used to group targets with similar roles together.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      A short, human-readable name for the subdivision.

      :nullable: False
      :type: String
      
   .. db:field:: description

      A field to store any descriptive information regarding the subdivision.

      :nullable: True
      :type: String
      
.. db:table:: credentials

   A table storing authentication information collected from a target during the
   course of a campaign.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: visit_id

      The identifier of the visit which submitted the credential information.

      :nullable: False
      :foreignkey: :db:fld:`visits.id`
            
   .. db:field:: message_id

      The identifier of the message which submitted the credential information.

      :nullable: False
      :foreignkey: :db:fld:`messages.id`
            
   .. db:field:: campaign_id

      The identifier campaign the information was collected as a part of.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: username

      The username submitted by the target.

      :nullable: True
      :type: String
      
   .. db:field:: password

      The password submitted by the target.

      :nullable: True
      :type: String
      
   .. db:field:: mfa_token

      The multi-factor authentication (MFA) token submitted by the target. This
      may, for example be a Time-Based One-Time Password (TOTP) code.

      :nullable: True
      :type: String
      
   .. db:field:: submitted

      The time at which the credential information was submitted.

      :nullable: True
      :type: DateTime
      
   .. db:field:: regex_validated

      Whether or not the fields passed validation with the regular expressions
      defined by the campaign at the time the credentials information was
      submitted. If no validation took place because no regular expressions were
      defined by the campaign, this field is null. If a regular expression
      for validation was defined for a field that was not submitted, validation
      fails and this field is false. See
      :py:func:`~validation.validate_credential` for more information.

      :nullable: True
      :type: Boolean
      
.. db:table:: deaddrop_connections

   A connection instance of an agent which has sent information to the server to
   prove that the agent was executed.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: deployment_id

      The deployment identifier of agent which initiated the connection.

      :nullable: False
      :foreignkey: :db:fld:`deaddrop_deployments.id`
            
   .. db:field:: campaign_id

      The identifier campaign the information was collected as a part of.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: count

      The number of times the agent made the connection with the same
      information, implying that the agent was executed multiple times.

      :nullable: True
      :type: Integer
      
   .. db:field:: ip

      The external IP address from which this information was submitted and
      collected from.

      :nullable: True
      :type: String
      
   .. db:field:: local_username

      The username that executed the agent.

      :nullable: True
      :type: String
      
   .. db:field:: local_hostname

      The hostname the agent was executed on.

      :nullable: True
      :type: String
      
   .. db:field:: local_ip_addresses

      The local IP addresses the agent identified on the system from which it
      was executed.

      :nullable: True
      :type: String
      
   .. db:field:: first_seen

      The first time the information was submitted to the server.

      :nullable: True
      :type: DateTime
      
   .. db:field:: last_seen

      The last time the information was submitted to the server.

      :nullable: True
      :type: DateTime
      
.. db:table:: deaddrop_deployments

   An instance of a generated agent which can be distributed as part of testing
   to identify users that are susceptible to executing arbitrary programs.

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: campaign_id

      The identifier of the campaign the deaddrop agent was generated for.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: destination

      A descriptive field describing where the agent was deployed to. Used for
      reporting and tracking purposes.

      :nullable: True
      :type: String
      
.. db:table:: industries

   An industry in which a company operates in.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      A short, human-readable name for the industry.

      :nullable: False
      :type: String
      
   .. db:field:: description

      A field to store any descriptive information regarding the industry.

      :nullable: True
      :type: String
      
.. db:table:: landing_pages

   A page that is intended to be visited during the course of a test to be
   qualified as a failure. Visits to the landing page will increment the
   :db:fld:`visits.count` field, while requests to non-landing pages will not.
   A campaign may have one or more landing pages, and they are automatically
   identified from the Target URL when messages are sent.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: campaign_id

      The identifier of the campaign this landing page is associated with.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: hostname

      The hostname component of the URL this landing page uses.

      :nullable: False
      :type: String
      
   .. db:field:: page

      The path component of the URL this landing page uses.

      :nullable: False
      :type: String
      
.. db:table:: messages

   A message that was sent to a target user to test their susceptibility to
   phishing attempts.

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: campaign_id

      The identifier of the campaign which this message was sent as a part of.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: target_email

      The email address of the user who this message was sent to.

      :nullable: True
      :type: String
      
   .. db:field:: first_name

      The first name of the user who this message was sent to.

      :nullable: True
      :type: String
      
   .. db:field:: last_name

      The last name of the user who this message was sent to.

      :nullable: True
      :type: String
      
   .. db:field:: opened

      The time at which the message was confirmed to have been opened. This
      field is prone to false negatives due to many email clients not
      automatically loading remote images.

      :nullable: True
      :type: DateTime
      
   .. db:field:: opener_ip

      The IP address which opened the message.

      :nullable: True
      :type: String
      
   .. db:field:: opener_user_agent

      The user agent of the request sent when the message was opened.

      :nullable: True
      :type: String
      
   .. db:field:: sent

      The time at which the message was sent to the target.

      :nullable: True
      :type: DateTime
      
   .. db:field:: reported

      The time at which the message was reported by the target.

      :nullable: True
      :type: DateTime
      
   .. db:field:: trained

      Whether or not the taget agreed to any training provided during the
      course of the testing.

      :nullable: True
      :type: Boolean
      
   .. db:field:: delivery_status

      A short, human-readable status regarding the state of delivery of the
      message such as delivered, rejected or deferred.

      :nullable: True
      :type: String
      
   .. db:field:: delivery_details

      Any additional details regarding the state of the message delivery status.

      :nullable: True
      :type: String
      
   .. db:field:: testing

      Whether or not the message was intended for testing and should be omitted
      from the overall results.

      :nullable: False
      :type: Boolean
      
   .. db:field:: company_department_id

      The identifier of the company subdivision that the target is a member of.

      :nullable: True
      :foreignkey: :db:fld:`company_departments.id`
            
.. db:table:: storage_data

   Storage for internal server data that is generated at run time.

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: created

      The time at which the data unit was created.

      :nullable: True
      :type: DateTime
      
   .. db:field:: modified

      The time at which the data unit was modified.

      :nullable: True
      :type: DateTime
      
   .. db:field:: namespace

      The namespace in which the data unit exists to allow the same
      :db:fld:`storage_data.key` to be used multiple times while remaining
      uniquely identifiable.

      :nullable: True
      :type: String
      
   .. db:field:: key

      The key by which the data unit is retrieved. This value must be unique
      within the defined :db:fld:`storage_data.namespace`.

      :nullable: False
      :type: String
      
   .. db:field:: value

      The readable and writable data unit itself, serialized as a binary object
      to be loaded and unloaded from the database.

      :nullable: True
      :type: Binary
      
.. db:table:: users

   An authorized user as loaded through the server's authentication mechanism.

   .. db:field:: expiration

      The time at which the user should no longer be able to authenticate to the
      server.

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      The name of the user.

      :nullable: False
      :type: String
      
   .. db:field:: description

      A field to store any descriptive information regarding the user.

      :nullable: True
      :type: String
      
   .. db:field:: phone_carrier

      The service provider of the user's cell phone. This information is used to
      send text messages via the providers email to SMS gateway.

      :nullable: True
      :type: String
      
   .. db:field:: phone_number

      The user's cell phone number. This information is used to provide the user
      with alerts regarding campaigns to which they have subscribed.

      :nullable: True
      :type: String
      
   .. db:field:: email_address

      The user's email address. This information is used to provide the user
      with alerts regarding campaigns to which they have been subscribed.

      :nullable: True
      :type: String
      
   .. db:field:: otp_secret

      A secret value used when prompting for Multi Factor Authentication (MFA)
      to the server.

      :nullable: True
      :type: String
      
   .. db:field:: last_login

      The time at which the user last authenticated.

      :nullable: True
      :type: DateTime
      
   .. db:field:: access_level

      The level of access available to a users, where a higher number represents
      less access than a lower number.

      :nullable: False
      :type: Integer
      
.. db:table:: visits

   An instance where a targeted user has failed their testing attempt by
   visiting the link provided to them from a message.

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: message_id

      The identifier of the message that was sent to the target which initiated
      the visit.

      :nullable: False
      :foreignkey: :db:fld:`messages.id`
            
   .. db:field:: campaign_id

      The identifier of the campaign that this visit is associated with.

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: count

      The number of times the user visited a landing page associated with the
      campaign. This would be the case when the user visits the link they were
      provided multiple times from the same browser.

      :nullable: True
      :type: Integer
      
   .. db:field:: ip

      The IP address from which the user visited the server.

      :nullable: True
      :type: String
      
   .. db:field:: details

      Any applicable details regarding the visist.

      :nullable: True
      :type: String
      
   .. db:field:: user_agent

      The user agent of the visist request.

      :nullable: True
      :type: String
      
   .. db:field:: first_landing_page_id

      The identifier of the first landing page the visit was made. This is used
      to determine which landing page a user visited if multiple landing pages
      are associated with the campaign.

      :nullable: True
      :foreignkey: :db:fld:`landing_pages.id`
            
   .. db:field:: first_seen

      The time at which the first visit was made to the server.

      :nullable: True
      :type: DateTime
      
   .. db:field:: last_seen

      The time at which the last visit was made to the server.

      :nullable: True
      :type: DateTime
