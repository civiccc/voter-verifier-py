# Defines the set of steps needed to create an image suitable for deploying the
# Verifier to Marathon.

FROM brigade/centos:7.4.1708-latest

# Copy all source code into the container
# See the .dockerignore file for a list of files that are excluded
COPY . /src

# Modify permissions so application user can access source files
RUN chown -R nobody /src
WORKDIR /src
