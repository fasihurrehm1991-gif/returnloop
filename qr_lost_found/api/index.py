import os
import sys
from pathlib import Path

import psycopg

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('VERCEL', '1')

import django

django.setup()

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application
from django.db import connection

call_command('collectstatic', interactive=False, verbosity=0)

if connection.vendor == 'postgresql':
    migration_database_url = (
        os.getenv('POSTGRES_URL_NON_POOLING')
        or os.getenv('DATABASE_URL')
    )
    if not migration_database_url:
        raise RuntimeError(
            'PostgreSQL migrations require a direct database URL.'
        )

    # Serialize migrations across simultaneous serverless cold starts.
    migration_lock_id = 0x52455455524E4C4F
    with psycopg.connect(
        migration_database_url,
        autocommit=True,
        connect_timeout=10,
    ) as lock_connection:
        lock_connection.execute(
            'SELECT pg_advisory_lock(%s)',
            (migration_lock_id,),
        )
        try:
            call_command('migrate', interactive=False, verbosity=0)
        finally:
            lock_connection.execute(
                'SELECT pg_advisory_unlock(%s)',
                (migration_lock_id,),
            )
else:
    call_command('migrate', interactive=False, verbosity=0)

app = get_wsgi_application()
