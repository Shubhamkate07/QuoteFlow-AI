import os
import unittest.mock
from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase


class CoreAPITests(APITestCase):
    def test_health_check_endpoint(self):
        """Verify the health check endpoint returns 200, healthy status, and database info."""
        url = reverse('health-check')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data.get('status'), 'healthy')
        self.assertEqual(response.data.get('service'), 'QuoteFlow AI API')
        self.assertIn('database', response.data)
        self.assertEqual(response.data['database'].get('status'), 'connected')
        self.assertIn('engine', response.data['database'])

    def test_api_root_endpoint(self):
        """Verify the API root returns discoverable endpoints."""
        url = reverse('api-root')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('endpoints', response.data)
        self.assertIn('health', response.data['endpoints'])
        self.assertIn('admin', response.data['endpoints'])

    def test_database_configuration_not_hardcoded(self):
        """
        Verify that database settings are dynamically bound from environment variables
        rather than hardcoded constants.
        """
        db_conf = settings.DATABASES['default']
        self.assertTrue(db_conf.get('ENGINE'))
        self.assertTrue(
            'postgresql' in db_conf['ENGINE'] or 'sqlite3' in db_conf['ENGINE'],
            f"Unexpected engine: {db_conf['ENGINE']}"
        )

        # Test that production settings dynamically read environment variables
        mock_env = {
            'DJANGO_ENV': 'production',
            'SECRET_KEY': 'test-prod-key-32-chars-long-for-testing-only',
            'ALLOWED_HOSTS': 'api.quoteflow.ai',
            'CORS_ALLOWED_ORIGINS': 'https://app.quoteflow.ai',
            'DB_NAME': 'dynamic_prod_db',
            'DB_USER': 'dynamic_prod_user',
            'DB_PASSWORD': 'dynamic_prod_password',
            'DB_HOST': 'db.internal.quoteflow.ai',
            'DB_PORT': '5433',
        }
        with unittest.mock.patch.dict(os.environ, mock_env):
            import importlib
            import config.settings.production as prod_module
            importlib.reload(prod_module)
            self.assertEqual(prod_module.DATABASES['default']['NAME'], 'dynamic_prod_db')
            self.assertEqual(prod_module.DATABASES['default']['USER'], 'dynamic_prod_user')
            self.assertEqual(prod_module.DATABASES['default']['HOST'], 'db.internal.quoteflow.ai')
            self.assertEqual(prod_module.DATABASES['default']['PORT'], '5433')
            self.assertEqual(prod_module.DATABASES['default']['ENGINE'], 'django.db.backends.postgresql')

    def test_django_admin_accessible(self):
        """Verify that Django admin is properly mounted and returns login page."""
        admin_login_url = reverse('admin:login')
        response = self.client.get(admin_login_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertContains(response, 'Django administration')

    def test_all_migrations_are_applied(self):
        """Verify that all core migrations have been applied successfully."""
        executor = MigrationExecutor(connection)
        targets = executor.loader.graph.leaf_nodes()
        unapplied = executor.migration_plan(targets)
        self.assertEqual(len(unapplied), 0, f"Unapplied migrations found: {unapplied}")
