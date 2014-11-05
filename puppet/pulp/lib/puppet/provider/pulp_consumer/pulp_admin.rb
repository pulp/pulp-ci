require "#{File.dirname(__FILE__)}/../../../puppet-pulp/pulp_admin"

Puppet::Type::type(:pulp_consumer).provide(:pulp_admin) do
  def create
    pulp_admin.register_consumer @resource[:id]
  end

  def destroy
    pulp_admin.unregister_consumer
  end

  def exists?
    consumer = pulp_admin.consumer
    !consumer.nil? && consumer.consumer_id == @resource[:id]
  end

  private

  def consumer
    pulp_admin.consumer
  end

  def pulp_admin
    PuppetPulp::PulpAdmin.new @resource[:login], @resource[:password]
  end
end
