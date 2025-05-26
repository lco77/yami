import os
from dotenv import load_dotenv
from celery import Celery
import tasks
load_dotenv()

# Config
REDIS_URL = os.environ.get("REDIS_URL")
RESULT_EXPIRES = 300

# Init app
worker = Celery('celery', broker=f"{REDIS_URL}/2", result_backend=f"{REDIS_URL}/2", task_ignore_result=False)
worker.conf.result_expires = RESULT_EXPIRES