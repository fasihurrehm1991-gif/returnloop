import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(PROJECT_ROOT)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
os.environ.setdefault('VERCEL', '1')

import django

django.setup()

from django.core.management import call_command
from django.core.wsgi import get_wsgi_application

call_command('migrate', interactive=False, verbosity=0)

app = get_wsgi_application()
