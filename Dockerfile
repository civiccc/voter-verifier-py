FROM brigade/centos:7.2.1511-latest

# Unfortunately we need to install this manually since the docker-compose
# executable isn't a single binary when installed via Homebrew, so we can't
# simply "mount" it. Thus we install the individual binary in the image itself
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
