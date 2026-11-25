"""
Django management command to clean up and recover stuck document processing and extraction tasks.
Usage:
    python manage.py recover_stuck_jobs [--minutes 10]
"""

from django.core.management.base import BaseCommand
from quotations.processing.recovery import recover_stuck_documents_and_extractions, get_stale_job_timeout_minutes


class Command(BaseCommand):
    help = "Recovers stuck document processing and AI extraction jobs older than N minutes."

    def add_arguments(self, parser):
        parser.add_argument(
            '--minutes',
            type=int,
            default=None,
            help=f"Age threshold in minutes (default: {get_stale_job_timeout_minutes()}).",
        )

    def handle(self, *args, **options):
        minutes = options.get('minutes')
        self.stdout.write(f"Scanning for stuck document processing and extraction jobs (timeout: {minutes or get_stale_job_timeout_minutes()}m)...")
        results = recover_stuck_documents_and_extractions(max_age_minutes=minutes)
        self.stdout.write(
            self.style.SUCCESS(
                f"Recovery complete: {results['recovered_documents']} document(s) and "
                f"{results['recovered_extractions']} extraction(s) marked as FAILED."
            )
        )
