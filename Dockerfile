# Defines the set of steps needed to create an image suitable for deploying the
# Verifier to Marathon.

FROM brigade/centos:7.2.1511-latest

# Copy all source code into the container
# See the .dockerignore file for a list of files that are excluded
ADD . /src
