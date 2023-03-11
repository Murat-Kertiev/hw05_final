from django.core.paginator import Paginator


def paginator_func(request, post_list, post_per_page=10):
    paginator = Paginator(post_list, post_per_page)
    page_number = request.GET.get('page')
    return paginator.get_page(page_number)
