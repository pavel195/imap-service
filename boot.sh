#!/bin/sh

NUM_WORKERS=3
TIMEOUT=600
# flask translate compile
# gunicorn --bind 0.0.0.0:5000 --access-logfile - --error-logfile  main:app \
gunicorn --bind 0.0.0.0:5000 main:app \
--workers $NUM_WORKERS \
--timeout $TIMEOUT
# gunicorn --bind 0.0.0.0:5000 main:app