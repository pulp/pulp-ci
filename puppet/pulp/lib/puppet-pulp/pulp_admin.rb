require 'yaml'
require 'ostruct'

module PuppetPulp
  class PulpAdmin
    attr_accessor :login, :password

    def initialize(username, password)
      @username = username
      @password = password
    end

    def create(repo_id, repo_type, params = {})
      login

      cmd = "pulp-admin #{repo_type} repo create --repo-id=#{repo_id}"

      [:display_name,
       :description,
       :feed,
       :serve_http,
       :serve_https,
       :relative_url,
       :feed_ca_cert,
       :feed_cert,
       :feed_key].each do |m|
        cmd << " --#{m.to_s.gsub '_', '-'}=\"#{params[m]}\"" unless params[m].nil?
      end

      if params[:queries]
        # only used for repo_type => puppet
        cmd << " --queries=\"#{params[:queries].join ','}\""
      end

      if params[:notes]
        cmd << " " + params[:notes].keys.sort.map { |k| "--note \"#{k}=#{params[:notes][k]}\"" }.join(' ')
      end

      output = `#{cmd}`
      raise "Could not create repo: #{output}" unless output =~ /Successfully created repository \[#{repo_id}\]/

      if params[:schedules]
        params[:schedules].each do |s|
          output = `pulp-admin #{repo_type} repo sync schedules create --repo-id=#{repo_id} -s #{s}`
          raise "Could not create schedule: #{output}" unless output =~ /Schedule successfully created/
        end
      end
    end

    def destroy(repo_id)
      login
      output = `pulp-admin "#{repo_type}" repo delete --repo-id="#{repo_id}"`
      raise "Could not remove repo: #{output}" unless output =~ /Repository \[#{repo_id}\] successfully deleted/
    end

    def repos(repo_type)
      login

      output = `pulp-admin #{repo_type} repo list --details`
      repos = parse_repos(output).map do |repo|
        description = repo['Description'] == 'None' ? nil : repo['Description']
        distributors_config = repo['Distributors']['Config']
        importers = repo['Importers']
        importers_config = importers['Config']
        feed = importers_config['Feed'] unless importers_config.nil?
        notes = repo['Notes'].nil? ? { } : repo['Notes']

        queries = importers_config && importers_config['Queries'] || ''
        queries = queries.split(/,/).map { |x| x.strip }

        schedules = importers && importers['Scheduled Syncs'] || ''
        schedules = schedules.split(/,/).map { |x| x.strip }

        serve_http = distributors_config['Serve Http'] unless distributors_config.nil?
        serve_http = serve_http.is_a?(String) ? serve_http == 'True' : true

        serve_https = distributors_config['Serve Https'] unless distributors_config.nil?
        serve_https = serve_https == 'True'

        relative_url = repo['Relative URL'].nil? ? { } : repo['Relative URL'] 

        props = {
          :id => repo['Id'],
          :display_name => repo['Display Name'],
          :description => description,
          :notes => notes,
          :feed => feed,
          :queries => queries,
          :schedules => schedules,
          :serve_http => serve_http,
          :serve_https => serve_https,
          :relative_url => relative_url,
        }

        # UGARY -- We might want to be 1.8-able one day
        result = Object.new
        singleton_class = class << result; self end

        setter = lambda do |val|
          `pulp-admin #{repo_type} repo update --repo-id=#{props[:id]} #{val}`
        end

        #getters
        props.each do |k,v|
          singleton_class.send(:define_method, k, lambda { v })
        end

        [:display_name,
         :description,
         :feed,
         :serve_http,
         :serve_https,
         :relative_url,
         :feed_cert,
         :feed_key ].each do |m|
          singleton_class.send :define_method, "#{m}=" do |v|
            setter.call "--#{m.to_s.gsub('_', '-')}=\"#{v}\""
          end
        end

        singleton_class.send :define_method, :queries= do |arr|
          setter.call "--queries=\"#{arr.join ','}\""
        end

        # Easier to test
        me = self
        singleton_class.send :define_method, :schedules= do |arr|
          repos = me.send :`, "pulp-admin #{repo_type} repo sync schedules list --repo-id=#{props[:id]}"
          repos.split(/\n/).each do |l|
            if l =~ /^Id:\s*(.+)/
              output = me.send :`, "pulp-admin #{repo_type} repo sync schedules delete --repo-id=#{props[:id]} --schedule-id=#{$1}"
              raise "Could not delete old schedule: #{output}" unless output =~ /Schedule successfully deleted/
            end
          end

          arr.each do |s|
            output = me.send :`, "pulp-admin #{repo_type} repo sync schedules create --repo-id=#{props[:id]} -s #{s}"
            raise "Could not create schedule: #{output}" unless output =~ /Schedule successfully created/
          end
        end

        singleton_class.send :define_method, :notes= do |map|
          notes = []
          map.keys.sort.each do |k|
            notes << "--note \"#{k}=#{map[k]}\""
          end
          setter.call notes.join ' '
        end

        result
      end

      repos.inject({}) do |memo,x|
        memo.merge!({x.id => x})
      end
    end

    def login
      unless @logged_in
        output =  `pulp-admin login -u #{@username} -p #{@password}`
        output =~ /Successfully logged in/ || raise("Could not login: #{output}")
      end
      @logged_in = true
    end

    def register_consumer(consumer_id)
      output = `pulp-consumer -u "#{@username}" -p "#{@password}" register --consumer-id="#{consumer_id}"`
      raise "Could not register consumer: #{output}" unless output =~ /Consumer \[#{consumer_id}\] successfully registered/
    end

    def unregister_consumer
      output = `pulp-consumer unregister`
      raise "Could not unregister consumer: #{output}" unless output =~ /Consumer \[.+\] successfully unregistered/
    end

    def consumer
      output = `pulp-consumer status`
      if output.gsub("\n", ' ') =~ /This consumer is registered to the server \[.+\] with the ID \[(.+)\]/
        OpenStruct.new :consumer_id => $1
      elsif output =~ /This consumer is not currently registered/
        nil
      else
        raise "Could not determine registration status: #{output}"
      end
    end

    private

    def parse_repos(str)
      repos = str.split /\n\n/

      #Throw away the header
      repos.shift

      #We get extra lines at the end of the input
      repos = repos.reject {|x| x.length == 1 }.map { |x| x.split /\n/ }

      repos.map { |x| parse_lines x }
    end

    def parse_lines(lines, indent = '')
      result = {}
      while lines && line = lines.shift
        if line =~ /^(#{indent}[^\s][^:]+):(\s*)(.*)$/
          name = $1.strip
          value = $3.strip
          if value.empty?
            value = parse_lines(lines, "#{indent}  ")
          else
            value_indent = ' ' * ($1.length + $2.length + 1)
            while lines && lines[0] =~ /^#{value_indent}[^\s+]/
              value += lines.shift.strip
            end
          end
          result[name] = value
        else
          lines.unshift line
          break
        end
      end
      result.empty? ? nil : result
    end
  end
end
