"""
Django management command to safely export and compress a PostgreSQL database backup.
Usage:
    python manage.py backup_database [--output-dir /backups]
"""

import gzip
import os
import shutil
import subprocess
from datetime import datetime
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Generates a compressed PostgreSQL database backup (.sql.gz) for QuoteFlow AI."

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            default=os.getenv('BACKUP_DIR', os.path.join(settings.BASE_DIR, 'backups')),
            help='Directory path where database backup files will be saved.',
        )

    def handle(self, *args, **options):
        db_config = settings.DATABASES.get('default', {})
        engine = db_config.get('ENGINE', '')

        if 'postgresql' not in engine:
            self.stdout.write(
                self.style.WARNING(
                    f"Default database is not PostgreSQL ({engine}). Skipping pg_dump backup."
                )
            )
            return

        db_name = db_config.get('NAME')
        db_user = db_config.get('USER')
        db_password = db_config.get('PASSWORD')
        db_host = db_config.get('HOST', 'localhost')
        db_port = str(db_config.get('PORT', '5432'))

        output_dir = options['output_dir']
        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        dump_filename = f"quoteflow_db_{timestamp}.sql.gz"
        dump_filepath = os.path.join(output_dir, dump_filename)

        pg_dump_cmd = shutil.which('pg_dump')
        if not pg_dump_cmd:
            raise CommandError("pg_dump executable was not found on PATH.")

        self.stdout.write(f"Initiating pg_dump for database '{db_name}' on {db_host}:{db_port}...")

        env = os.environ.copy()
        if db_password:
            env['PGPASSWORD'] = str(db_password)

        dump_proc = subprocess.Popen(
            [
                pg_dump_cmd,
                '-h', str(db_host),
                '-p', str(db_port),
                '-U', str(db_user),
                '-F', 'c',
                '-b',
                str(db_name),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )

        with gzip.open(dump_filepath, 'wb') as gz_out:
            shutil.copyfileobj(dump_proc.stdout, gz_out)

        _, stderr = dump_proc.communicate()

        if dump_proc.returncode != 0:
            if os.path.exists(dump_filepath):
                os.remove(dump_filepath)
            raise CommandError(f"pg_dump failed with exit code {dump_proc.returncode}: {stderr.decode('utf-8')}")

        size_mb = os.path.getsize(dump_filepath) / (1024 * 1024)
        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully created database backup: {dump_filepath} ({size_mb:.2f} MB)"
            )
        )
