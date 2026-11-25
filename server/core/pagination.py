import os
from rest_framework.pagination import PageNumberPagination


class StandardResultsSetPagination(PageNumberPagination):
    """
    Standard pagination class supporting dynamic page_size query parameter.
    Allows clients to request custom page sizes up to max_page_size (1000).
    """
    page_size = int(os.getenv('DRF_PAGE_SIZE', '20'))
    page_size_query_param = 'page_size'
    max_page_size = 1000
