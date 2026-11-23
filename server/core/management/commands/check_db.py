"""
Django management command to check database connection, migration state,
Django admin readiness, and verify environment variable-driven settings.
"""

from django.core.management.base import BaseCommand
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve


class Command(BaseCommand):
    help = "Verifies database connectivity, migrations, admin readiness, and settings source."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("=== QuoteFlow AI Database Diagnostic ==="))
        
        settings_dict = connection.settings_dict
        engine = settings_dict.get('ENGINE', '')
        name = str(settings_dict.get('NAME', ''))
        user = settings_dict.get('USER', '')
        host = settings_dict.get('HOST', '')
        port = str(settings_dict.get('PORT', ''))
        conn_max_age = settings_dict.get('CONN_MAX_AGE', 0)

        self.stdout.write(f"Engine:       {engine}")
        self.stdout.write(f"Database:     {name}")
        self.stdout.write(f"User:         {user or '(default)'}")
        self.stdout.write(f"Host:         {host or 'localhost'}")
        self.stdout.write(f"Port:         {port or '5432'}")
        self.stdout.write(f"Conn Max Age: {conn_max_age}s")

        # 1. Connection check
        self.stdout.write("\nTesting database connection...")
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1;")
                if 'postgresql' in engine:
                    cursor.execute("SELECT version();")
                    pg_version = cursor.fetchone()[0]
                    self.stdout.write(self.style.SUCCESS("[PASS] Connected to PostgreSQL successfully."))
                    self.stdout.write(f"       Server: {pg_version}")
                else:
                    self.stdout.write(self.style.SUCCESS(f"[PASS] Connected to {connection.vendor} database successfully."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Could not connect to database:\n       {str(e)}"))
            self.stdout.write(
                self.style.WARNING(
                    "\n--- Connection Troubleshooting Tips ---\n"
                    "1. Is PostgreSQL running on Windows?\n"
                    "   Run in PowerShell: Get-Service *postgres* or net start postgresql-x64-16\n"
                    "2. Does the database exist?\n"
                    "   Run: psql -U postgres -c \"CREATE DATABASE quoteflow_db;\"\n"
                    "3. Check server/.env values (DB_NAME, DB_USER, DB_PASSWORD, DB_HOST, DB_PORT)\n"
                    "4. If PostgreSQL is not yet running, set USE_SQLITE=True in server/.env for local dev fallback.\n"
                )
            )
            return

        # 2. Migrations check
        self.stdout.write("\nChecking migration status...")
        try:
            executor = MigrationExecutor(connection)
            targets = executor.loader.graph.leaf_nodes()
            unapplied = executor.migration_plan(targets)
            if unapplied:
                self.stdout.write(
                    self.style.WARNING(
                        f"[WARN] {len(unapplied)} unapplied migration(s) detected. Run: python manage.py migrate"
                    )
                )
                for migration, _ in unapplied:
                    self.stdout.write(f"       - {migration.app_label}: {migration.name}")
            else:
                self.stdout.write(self.style.SUCCESS("[PASS] All database migrations are up to date."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Error checking migrations: {str(e)}"))

        # 3. Admin check
        self.stdout.write("\nChecking Django Admin readiness...")
        try:
            admin_url = reverse('admin:index')
            resolved_view = resolve(admin_url)
            self.stdout.write(self.style.SUCCESS(f"[PASS] Admin route resolved: {admin_url} -> {resolved_view.func.__name__}"))

            User = get_user_model()
            superuser_count = User.objects.filter(is_superuser=True).count()
            if superuser_count > 0:
                self.stdout.write(self.style.SUCCESS(f"[PASS] {superuser_count} active superuser(s) found."))
            else:
                self.stdout.write(
                    self.style.WARNING(
                        "[INFO] No superusers exist yet. Create one by running: python manage.py createsuperuser"
                    )
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"[FAIL] Error checking admin: {str(e)}"))

        self.stdout.write(self.style.SUCCESS("\n[COMPLETED] Diagnostic finished."))
