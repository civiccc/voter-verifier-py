***REMOVED***
EXPOSE 3000
WORKDIR /app
# TODO: Add logging stuff
RUN touch /var/lib/rpm/{,*} \
  && yum clean all \
  && yum install -y git wget
RUN useradd app \
  && wget -O /usr/bin/gosu https://github.com/tianon/gosu/releases/download/1.4/gosu-amd64 \
  && chmod +x /usr/bin/gosu
***REMOVED***
  && chmod +x /usr/bin/pv
RUN easy_install virtualenv
ADD entrypoint.sh /usr/local/bin/entrypoint
ENTRYPOINT ["/usr/local/bin/entrypoint"]
