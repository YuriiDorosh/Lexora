#!/bin/bash

# celery -A src.celery_app.app worker -l info --hostname=worker1@%h
celery -A src.celery_app:app worker -l info --hostname=worker1@%h