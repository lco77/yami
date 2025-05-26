FROM python:3.12

# create venv
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

ENV FLASK_APP=app
ENV FLASK_ENV=production

ENV REDIS_URL="redis://yami"

ENV LDAP_HOST="ldaps.straumann.com"
ENV LDAP_USERNAME="CN=app_nwsldp,OU=special_users,OU=ch01,OU=users,OU=prod,OU=_straumann,DC=straumann,DC=com"
ENV LDAP_PASSWORD="LzXmxSa6"
ENV LDAP_BASE_DN="OU=prod,OU=_straumann,DC=straumann,DC=com"
ENV LDAP_ROLES='{"admin": ["CN=dl_all_radius_admin_rights","CN=dl_all_lan_admin_rights"], "read-only": []}'

ENV DNAC_HOST="ch01s090-dnac-data.straumann.com"
ENV DNAC_USERNAME="api-read-only"
ENV DNAC_PASSWORD="UGgbUAhzke9vSb8i8AhJ"

ENV DNS_SERVERS='["10.60.103.5","10.60.103.69"]'
ENV DNS_SUFFIXES='["nws.straumann.com","straumann.com"]'


# create a group and user
RUN groupadd -g 1000 yami && useradd --no-create-home -r -u 1000 -g yami yami

# copy requirements.txt
COPY /requirements.txt /

# upgrade pip, install wheel and requirements

RUN pip install --upgrade pip
RUN pip install wheel
RUN pip install -r requirements.txt

# SETUP TINI
#ENV TINI_VERSION v0.19.0
#RUN curl -L https://github.com/krallin/tini/releases/download/${TINI_VERSION}/tini -o /tini
#RUN chmod +x /tini

# copy every content to the image
COPY --chown=yami:yami /yami /yami

# change user
USER yami

# expose listening port
EXPOSE 5000

#set entrypoint
CMD ["gunicorn", "--chdir", ".", "--bind", "0.0.0.0:5000", "app:app", "--workers", "1", "--threads", "5"]