FROM centos:7.4.1708

# Copy all source code into the container
# See the .dockerignore file for a list of files that are excluded
COPY . /src

# Modify permissions so application user can access source files
RUN chown -R nobody /src
WORKDIR /src
