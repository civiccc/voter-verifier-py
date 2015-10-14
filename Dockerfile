***REMOVED***
EXPOSE 3000
WORKDIR /app
CMD ["env/bin/gunicorn", "web:app", "-b", "0.0.0.0:3000", "--log-file=-"]

# Install all the system dependencies
# Doing this before the "ADD . /app" makes it so that these will be cached
# between builds.
RUN touch /var/lib/rpm/{.,}* && \
    yum clean all && \
    yum install -y git python-devel && \
    yum clean all && \
    easy_install virtualenv && \
    virtualenv env

# Install the python dependencies
# Adding this file individually allows Docker to cache these steps if the
# requirements.txt file does not change.
ADD requirements.txt /tmp/requirements.txt
RUN source env/bin/activate && \
    pip install -r /tmp/requirements.txt

ADD . /app
