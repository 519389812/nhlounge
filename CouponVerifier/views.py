from django.shortcuts import redirect, reverse


def check_authority(func):
    def wrapper(*args, **kwargs):
        if not args[0].user.is_authenticated:
            # if "X-Requested_With" in args[0].headers:
            #     return JsonResponse('请先登录', safe=False, json_dumps_params={'ensure_ascii': False})
            if args[0].META['QUERY_STRING']:
                return redirect(reverse('verification:login') + '?next=%s?%s' % (args[0].path, args[0].META['QUERY_STRING']))
            return redirect(reverse('verification:login') + '?next=%s' % args[0].path)
        return func(*args, **kwargs)
    return wrapper
