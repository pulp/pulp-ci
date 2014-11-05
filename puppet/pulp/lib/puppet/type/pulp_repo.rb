require 'puppet/type'
require 'uri'

Puppet::Type.newtype(:pulp_repo) do
  ensurable

  newparam(:id) do
    desc 'The repo id'
    isnamevar
    validate do |v|
      raise 'name may contain only alphanumberic, ., -, and _' unless v =~ /^[A-Za-z0-9\.\-_]+$/
    end
  end

  newparam(:repo_type) do
      desc 'Repo content description'

      newvalues(:rpm, :puppet)

      defaultto "rpm"
  end

  newproperty(:display_name) do
      desc 'Pulp display name'
  end

  newproperty(:description) do
      desc "Pulp repo description"
  end

  newproperty(:feed) do
    validate do |v|
      raise 'feed must be a valid url' unless v =~ URI::regexp
    end
  end
  
  newproperty(:notes) do
    validate do |v|
      raise 'notes must be a map' unless v.is_a? Hash
    end
  end

  newproperty(:validate) do
    munge do |v|
        v.to_s == 'true'
    end 
    
    validate do |v|
      raise 'validate be a boolean value' unless (['true', 'false'] & [v.to_s]).any?
    end
  end

  newproperty(:queries) do
    queries = []
    munge do |v|
        queries << v
    end
  end

  newproperty(:schedules) do
    schedules = []
    munge do |v|
        schedules << v
    end
  end

  newproperty(:serve_http) do
      munge do |v|
          v.to_s == 'true'
      end

    validate do |v|
      raise 'serve_http must be a boolean value' unless (['true', 'false'] & [v.to_s]).any?
    end
  end

  newproperty(:serve_https) do
      munge do |v|
          v.to_s == 'true'
      end

    validate do |v|
      raise 'serve_https must be a boolean value' unless (['true', 'false'] & [v.to_s]).any?
    end
  end

  newproperty(:relative_url) do
    desc "URL repo will be hosted at"
    validate do |v|
      raise 'name may contain only alphanumberic, ., -, /, and _' unless v =~ /^[A-Za-z0-9\.\-_\/]+$/
    end
  end

  newproperty(:feed_ca_cert) do
      desc "CA cert for feed"
  end

  newproperty(:feed_cert) do
      desc "Client certificate to use for feed"
  end

  newproperty(:feed_key) do
      desc "Client key to use for feed"
  end

  newproperty(:verify_ssl) do
      munge do |v|
          v.to_s == 'true'
      end

    validate do |v|
      raise 'serve_https must be a boolean value' unless (['true', 'false'] & [v.to_s]).any?
    end
  end

   newparam(:login) do
     defaultto "admin"
   end

    newparam(:password) do
        defaultto "admin"
    end

  validate do
    fail 'must specify login' if self[:login].to_s.empty?
    fail 'must specify password' if self[:password].to_s.empty?
  end
end
