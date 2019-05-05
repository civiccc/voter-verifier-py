set -euo pipefail

source /***REMOVED***
source /***REMOVED***

# Need to include Python version since some packages may link against libraries
# specific to that version
env-artifact-name() {
  echo "env-$(python --version 2>&1 | tr ' ' '-')"
}

install-python-packages() {
  local artifact_name="$(env-artifact-name)"
  local artifact_path="$(git rev-parse --show-toplevel)/env"
  local cache_key="$(fingerprint requirements.txt)"
  local cache_path="$HOME/.cache/$artifact_name/${cache_key}"

  if [ ! -d "$artifact_path" ]; then
    section "Installing Python packages in virtual environment..."
    with-artifact setup-virtualenv "$cache_key" "$cache_path" "$artifact_name" "$artifact_path"
  fi
}

activate-virtualenv() {
  # We need to define a PS1 prompt so that this script works
  PS1='[\h \W]\$ ' source env/bin/activate
}

setup-virtualenv() {
  (virtualenv env && \
    activate-virtualenv && \
    pip install -r requirements.txt --no-cache-dir && \
    virtualenv --relocatable env)
}

wait-for-elasticsearch() {
  echo "Waiting for Elasticsearch..."
  dockerize -timeout 30s -wait http://${ELASTICSEARCH_HOST:-127.0.0.1}:9200 \
    echo "Elasticsearch ready!" && return

  error "Could not connect to Elasticsearch!"
  docker-compose logs --tail=20 elasticsearch
  return 1
}

# We need to vary this name based on the Ruby version since native extensions
# are compiled against the Ruby libraries present, meaning some gems are not
# transferrable between Ruby versions.
gems-artifact-name() {
  echo "gems-$(cat .ruby-version)"
}

install-gems() {
  local artifact_name="$(gems-artifact-name)"
  local artifact_path=/usr/local/bundle
  local cache_key="$(fingerprint Gemfile Gemfile.lock)"
  local cache_path="$HOME/.cache/$artifact_name/${cache_key}"

  section "Installing gems..."
  with-artifact download-gems "$cache_key" "$cache_path" "$artifact_name" "$artifact_path"
}

download-gems() {
  local artifact_name="$(gems-artifact-name)"
  local artifact_path=/usr/local/bundle

  local bundler_version=$(awk '/DEPENDENCIES/,/ bundler /' Gemfile.lock | tail -n1 | grep -oE '[0-9\.]+')

  # Attempt to download latest gem bundle with the hope that it won't be too
  # different from the one for current Gemfile. This significantly speeds up
  # test runs which make changes to the Gemfile, since we don't generate the
  # bundle from scratch.
  if download-latest-artifact "$artifact_name" "$artifact_path"; then
    echo "Downloaded latest '$artifact_name' bundle as base."
    echo "Installing new gems on top of base and then pruning unused gems..."
  else
    warn "WARN: Unable to download latest '$artifact_name' artifact. Installing from scratch..."
  fi

  echo "Installing gem bundle..."
  chronic gem install bundler --conservative --version $bundler_version
  chronic bundle install --jobs=$(nproc) --retry=3 --clean
}
