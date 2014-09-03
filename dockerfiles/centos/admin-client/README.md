# Running pulp-admin as a Docker container

The pulp-admin client may be run as a container.

## Setup

1. The `~/.pulp` directory will be mounted when the container is run. Add the pulp server hostname and any other configuration values to `~/.pulp/admin.conf`. If the pulp server SSL certificate is not CA-signed use `verify_ssl = false`.

        [server]
        host = pulp-server.example.com
        verify_ssl = true

1. Pull the pulp-admin image

        docker pull pulp/pulp-admin

1. Create a directory for uploads for the output of `docker save`, for example, `/tmp/pulp_uploads/`. This will be mapped to the container so local files may be uploaded from the container. Use this in the next step.

1. Create an alias for `pulp-admin`. For example, update your `$HOME/.bashrc` file with the line below and run `source $HOME/.bashrc`.

        alias pulp-pulp="sudo docker run --rm -t -v $HOME/.pulp:/.pulp -v /tmp/pulp_uploads/:/tmp/pulp_uploads/ pulp/pulp-admin"

## About

* based on centos image
* adds pulp_docker plugin
* The `--rm` flag adds about 4 seconds to runtime but will remove the container when complete.
