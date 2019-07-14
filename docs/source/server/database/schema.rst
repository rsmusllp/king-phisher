.. _database-schema-label:

Schema
======

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

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
.. db:table:: credentials

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: visit_id

      :nullable: False
      :foreignkey: :db:fld:`visits.id`
            
   .. db:field:: message_id

      :nullable: False
      :foreignkey: :db:fld:`messages.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: username

      :nullable: True
      :type: String
      
   .. db:field:: password

      :nullable: True
      :type: String
      
   .. db:field:: mfa_token

      :nullable: True
      :type: String
      
   .. db:field:: submitted

      :nullable: True
      :type: DateTime
      
   .. db:field:: regex_validated

      :nullable: True
      :type: Boolean
      
.. db:table:: deaddrop_connections

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: deployment_id

      :nullable: False
      :foreignkey: :db:fld:`deaddrop_deployments.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: count

      :nullable: True
      :type: Integer
      
   .. db:field:: ip

      :nullable: True
      :type: String
      
   .. db:field:: local_username

      :nullable: True
      :type: String
      
   .. db:field:: local_hostname

      :nullable: True
      :type: String
      
   .. db:field:: local_ip_addresses

      :nullable: True
      :type: String
      
   .. db:field:: first_seen

      :nullable: True
      :type: DateTime
      
   .. db:field:: last_seen

      :nullable: True
      :type: DateTime
      
.. db:table:: deaddrop_deployments

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: destination

      :nullable: True
      :type: String
      
.. db:table:: industries

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
.. db:table:: landing_pages

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: hostname

      :nullable: False
      :type: String
      
   .. db:field:: page

      :nullable: False
      :type: String
      
.. db:table:: messages

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: target_email

      :nullable: True
      :type: String
      
   .. db:field:: first_name

      :nullable: True
      :type: String
      
   .. db:field:: last_name

      :nullable: True
      :type: String
      
   .. db:field:: opened

      :nullable: True
      :type: DateTime
      
   .. db:field:: opener_ip

      :nullable: True
      :type: String
      
   .. db:field:: opener_user_agent

      :nullable: True
      :type: String
      
   .. db:field:: sent

      :nullable: True
      :type: DateTime
      
   .. db:field:: reported

      :nullable: True
      :type: DateTime
      
   .. db:field:: trained

      :nullable: True
      :type: Boolean
      
   .. db:field:: delivery_status

      :nullable: True
      :type: String
      
   .. db:field:: delivery_details

      :nullable: True
      :type: String
      
   .. db:field:: testing

      :nullable: False
      :type: Boolean
      
   .. db:field:: company_department_id

      :nullable: True
      :foreignkey: :db:fld:`company_departments.id`
            
.. db:table:: storage_data

   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: created

      :nullable: True
      :type: DateTime
      
   .. db:field:: modified

      :nullable: True
      :type: DateTime
      
   .. db:field:: namespace

      :nullable: True
      :type: String
      
   .. db:field:: key

      :nullable: False
      :type: String
      
   .. db:field:: value

      :nullable: True
      :type: Binary
      
.. db:table:: users

   .. db:field:: expiration

      :nullable: True
      :type: DateTime
      
   .. db:field:: id

      :primarykey: True
      :type: Integer
      
   .. db:field:: name

      :nullable: False
      :type: String
      
   .. db:field:: description

      :nullable: True
      :type: String
      
   .. db:field:: phone_carrier

      :nullable: True
      :type: String
      
   .. db:field:: phone_number

      :nullable: True
      :type: String
      
   .. db:field:: email_address

      :nullable: True
      :type: String
      
   .. db:field:: otp_secret

      :nullable: True
      :type: String
      
   .. db:field:: last_login

      :nullable: True
      :type: DateTime
      
   .. db:field:: access_level

      :nullable: False
      :type: Integer
      
.. db:table:: visits

   .. db:field:: id

      :primarykey: True
      :type: String
      
   .. db:field:: message_id

      :nullable: False
      :foreignkey: :db:fld:`messages.id`
            
   .. db:field:: campaign_id

      :nullable: False
      :foreignkey: :db:fld:`campaigns.id`
            
   .. db:field:: count

      :nullable: True
      :type: Integer
      
   .. db:field:: ip

      :nullable: True
      :type: String
      
   .. db:field:: details

      :nullable: True
      :type: String
      
   .. db:field:: user_agent

      :nullable: True
      :type: String
      
   .. db:field:: first_landing_page_id

      :nullable: True
      :foreignkey: :db:fld:`landing_pages.id`
            
   .. db:field:: first_seen

      :nullable: True
      :type: DateTime
      
   .. db:field:: last_seen

      :nullable: True
      :type: DateTime
      

