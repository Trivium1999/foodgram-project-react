from rest_framework.pagination import PageNumberPagination


class RecipePagination(PageNumberPagination):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.page_size_query_param = 'limit'

# class Pagination:
#     def set_query_params(self, request):
#         if hasattr(request, '_query_params'):
#             return
#         params = {
#             'page_size': self.get_page_size(),
#             'page_range': self.get_page_range(),
#             'page_size_query_param': 'limit',
#         }
#         request._query_params = params
