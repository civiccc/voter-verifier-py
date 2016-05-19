# Defines the set up steps necessary to create an image to use Dock with this
# repository, allowing you to easily develop or test the Verifier.

FROM brigade/centos:7.2.1511-latest

# Install Docker-related software. We can't just mount the host executables in
# the container since the host may be a Mac and thus using a different build
***REMOVED***
    | tar -xzf - -C /usr/local/bin --strip-components=3 \
    && chmod +x /usr/local/bin/docker \
***REMOVED***
    | tar -xzf - -C /usr/local/bin \
    && chmod +x /usr/local/bin/docker-compose

RUN yum install -y \
  # Needed to install virtualenv via easy_install
  python-setuptools \
  # Used by Chronos job to do monthly imports
  pv \

  # Used to maintain isolated Python environment in the repo
  && easy_install virtualenv \
  && yum clean all
