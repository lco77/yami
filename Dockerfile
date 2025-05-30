FROM python:3.12

# create venv
ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

# create a group and user
RUN groupadd -g 1000 yami && useradd --no-create-home -r -u 1000 -g yami yami

# copy requirements.txt
COPY /requirements.txt /

# upgrade pip, install wheel and requirements
RUN pip install --upgrade pip
RUN pip install wheel
RUN pip install -r requirements.txt

# copy every content to the image
RUN mkdir /yami
COPY --chown=yami:yami / /yami

# change user
USER yami

# expose listening port
EXPOSE 5000

#set entrypoint
CMD ["gunicorn", "--chdir", "/yami", "--bind", "0.0.0.0:5000", "app:app", "--workers", "1", "--threads", "4"]