# yami - yet another management interface (for your network)

Yami is an early stage project, which aims at facilitating network operations for network engineers and IT support colleagues.


## Roadmap

- Cisco DNAC integration

Browse and troubleshoot LAN devices. Possibly perform basic NMS operations with them.

- Cisco SDWAN integration

Browse and troubleshoot WAN devices. Possibly perform basic NMS operations with them.

- Cisco Meraki Wireless integration

Browse and troubleshoot Meraki Wireless devices. Possibly perform basic NMS operations with them.


## High level architecture

- LDAP authentication with group to role mapping (typically for use with Active Directory)
- Celery integration to offload long running tasks
- Clear UI versus API separation
- Server-side sessions
- Minimalist Bootstrap frontend using JQuery only
- Support for Dark/Light theme
- Configuration from environment variables only
- Stateless application without persistent storage requirements


## Installation

```shell
python -m venv venv
. .\venv\Scripts\activate
python -m pip install --upgrade pip

```

## Configuration

Just add environment variables

```shell
# your application name
FLASK_APP="yami"

# set to 'development' or 'production'
FLASK_ENV="development"

# define LDAP credentials
# Note: the application defaults to LDAPS without TLS certificate verification
LDAP_HOST="ldap.company.com"
LDAP_USERNAME="CN=ldap_user,DC=company,DC=com"
LDAP_PASSWORD="password"
LDAP_BASE_DN="DC=company,DC=com"

# use a JSON formatted string to map roles with AD groups
# you can map multiple groups per role
# Note: a user can match multiple roles
LDAP_ROLES='{"admin": ["CN=admin_users"], "read-only": ["CN=read_users"]}'

# REDIS setup (required by Celery)
REDIS_URL="redis://localhost"

# Cisco DNAC
DNAC_HOST="dnac.company.com"
DNAC_USERNAME="username"
DNAC_PASSWORD="password"

# DNS resolution
DNS_SERVERS='["10.0.0.2","10.0.0.3"]'
DNS_SUFFIXES='["net.company.com","company.com"]'


```


## Basic Usage

During app development, simply start your app from the app directory

```shell
# start Flask
flask run --reload

# or using watchog to catch any file change
pip install watchdog
watchmedo auto-restart --patterns="*.py;*.html;*.css;*.js;.env" --recursive -- flask run

# start Celery worker (Linux)
celery -A worker worker --loglevel=INFO


# start Celery worker (Windows)
celery -A worker worker --pool=solo --loglevel=INFO
```

## Access control

There are 2 decorators which you can use to restrict access to your routes:

- @login_required()

A valid authenticated user is required

- @roles_required(allowed_roles)

A valid authenticated user with at least one of allowed_roles is required


