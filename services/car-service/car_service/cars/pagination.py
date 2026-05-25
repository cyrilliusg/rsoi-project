from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class ApiPagination(PageNumberPagination):
    page_query_param = "page"  # ?page=
    page_size_query_param = "size"  # ?size=
    page_size = 10  # значение по умолчанию
    max_page_size = 100  # на всякий случай

    def get_paginated_response(self, data):
        return Response({
            "page": self.page.number,
            # фактический размер текущей страницы (на последней может быть меньше)
            "pageSize": len(data),
            "totalElements": self.page.paginator.count,
            "items": data,
        })
