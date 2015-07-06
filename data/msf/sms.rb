# Copyright (c) 2015, Brandan [coldfusion]
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

require 'uri'
module Msf

  class Plugin::SessionSMS < Msf::Plugin
    include Msf::SessionEvent

    if not defined?(Sms_yaml)
      Sms_yaml = "#{Msf::Config.get_config_root}/sms.yaml"
    end

    def initialize(framework, opts)
      super
      add_console_dispatcher(SMSCommandDispatcher)
    end

    def cleanup
      self.framework.events.remove_session_subscriber(@inst)
      remove_console_dispatcher('sms')
    end

    def name
      "sms"
    end

    def desc
      "Sends a SMS message when recieving a new session through the use of the King Phisher's REST API."
    end

    class SMSCommandDispatcher < Plugin::SessionSMS
      include Msf::Ui::Console::CommandDispatcher

      @king_phisher_server = nil
      @king_phisher_token = nil
      @sms_number =  nil
      @sms_carrier =  nil

      def on_session_open(session)
        print_status("Session received sending SMS...")
        begin
          http_client = Rex::Proto::Http::Client.new("#{@king_phisher_server}")
          http_client.connect
          request = http_client.request_cgi({
            'uri'    => '/_/api/sms/send',
            'query'  => "token=#{@king_phisher_token}&message=Shells+On+Deck!!+Session:+#{session.sid}&phone_number=#{@sms_number}&carrier=#{@sms_carrier}"
          })
          response = http_client.send_recv(request)
        rescue Exception => e
          print_error("Exception occured, you done goofed!")
        ensure
          http_client.close
        end
      end

      def name
        "sms"
      end

      def read_settings
        read = nil
        if File.exist?(Sms_yaml)
          ldconfig = YAML.load_file("#{Sms_yaml}")
          @king_phisher_server = ldconfig['king_phisher_server']
          @king_phisher_token = ldconfig['king_phisher_token']
          @sms_number = ldconfig['sms_number']
          @sms_carrier = ldconfig['sms_carrier']
          read = true
        else
          return read
        end
        return read
      end

      def commands
        {
          'sms_start'    => "Start SMS alerts for new sessions",
          'sms_stop'    => "Stop SMS alerts for new sessions",
          'sms_save'    => "Save SMS settings to #{Sms_yaml}",
          'sms_set_server'  => "Set domain name of the King Phisher server",
          'sms_set_token'    => "Set King Phisher's API token",
          'sms_set_number'  => "Set number to send SMS alerts to on new session",
          'sms_set_carrier'  => "Set carrier for sending SMS messages",
          'sms_show_params'  => "Shows currently set or saved parameters"
        }
      end

      def cmd_sms_start
        if read_settings()
          self.framework.events.add_session_subscriber(self)
          print_good("Starting SMS plugin, monitoring sessions...")
        else
          print_error("Could not read SMS settings!")
        end
      end

      def cmd_sms_stop
        print_good("Stopping SMS alerting!")
        self.framework.events.remove_session_subscriber(self)
      end

      def cmd_sms_save
        if @king_phisher_server and @king_phisher_token and @sms_number and @sms_carrier
          config = {
            'king_phisher_server' => @king_phisher_server,
            'king_phisher_token' => @king_phisher_token,
            'sms_number' => @sms_number,
            'sms_carrier' => @sms_carrier
          }
          File.open(Sms_yaml, 'w') do |out|
            YAML.dump(config, out)
          end
          print_good("All parameters saved to #{Sms_yaml}")
        else
          print_error("You have not provided all the parameters!")
        end
      end

      def cmd_sms_set_server(*args)
        if args.length > 0
          print_status("Setting the King Phisher server to #{args[0]}")
          @king_phisher_server = args[0]
        else
          print_error("Please provide the domain name of your King Phisher server!")
        end
      end

      def cmd_sms_set_token(*args)
        if args.length > 0
          print_status("Setting King Phisher's REST API token to #{args[0]}")
          @king_phisher_token = args[0]
        else
          print_error("Please provide the REST API token of your King Phisher server!")
        end
      end

      def cmd_sms_set_number(*args)
        if args[0].length == 10 
          print_status("Setting SMS number to #{args[0]}")
          @sms_number = args[0]
        else
          print_error("Please provide a valid SMS number!")
        end
      end

      def cmd_sms_set_carrier(*args)
        if args.length > 0 and ['AT&T', 'Boost', 'Sprint', 'T-Mobile', 'Verizon', 'Virgin Mobile'].include? "#{args[0]}"
          print_status("Setting SMS carrier to #{args[0]}")
          @sms_carrier = args[0]
        else
          print_error("Please provide a valid SMS carrier (AT&T, Boost, Sprint, T-Mobile, Verizon, Virgin Mobile)!")
        end
      end

      def cmd_sms_show_params
        if read_settings()
          print_status("Parameters:")
          print_good("King Phisher Server: #{@king_phisher_server}")
          print_good("King Phisher Token: #{@king_phisher_token}")
          print_good("SMS Number: #{@sms_number}")
          print_good("SMS Carrier: #{@sms_carrier}")
        else
          print_error("Could not read settings from #{Sms_yaml}!")
        end
      end
    end
  end
end