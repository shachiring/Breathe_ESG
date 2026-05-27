#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
python manage.py shell -c "from emissions.models import Tenant; Tenant.objects.get_or_create(id=1, defaults={'name': 'Acme Corp'})"
