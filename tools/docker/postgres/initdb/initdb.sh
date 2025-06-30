#!/bin/bash

set -eux

database=${POSTGRESQL_DATABASE}

echo "Creating database '$database'"
psql -v ON_ERROR_STOP=1 --username "$POSTGRESQL_USER" <<-EOSQL
	CREATE DATABASE $database;
EOSQL