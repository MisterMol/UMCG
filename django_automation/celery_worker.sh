#!/bin/sh

exec celery -A umcg_project worker \
    --loglevel=info
