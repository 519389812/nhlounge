import datetime
from django.shortcuts import render, redirect, reverse
from verification.models import Coupon
from pytz import timezone
from CouponVerifier.settings import TIME_ZONE, AUTH_USER_MODEL
from CouponVerifier.rsa_handler import RsaHandler
from django.contrib import messages
from django.contrib.auth import authenticate
from django.contrib.auth import login as login_admin
from django.contrib.auth import logout as logout_admin
from django.contrib.auth.hashers import check_password
from CouponVerifier.views import check_authority
from urllib import parse


time_zone = timezone(TIME_ZONE)


@check_authority
def home(request):
    return render(request, 'verification.html')


# 解析url中的参数
def parse_url_param(url):
    url_content = parse.urlparse(url)
    query_dict = parse.parse_qs(url_content.query)
    return query_dict


@check_authority
def verify(request):
    if request.method == "POST":
        coupon_code = request.POST.get("coupon", "")
        if not coupon_code:
            messages.error(request, "请输入券码")
            return redirect(reverse('verification:home'))
        try:
            coupon = Coupon.objects.get(coupon=coupon_code)
        except:
            messages.error(request, "未找到该券码")
            return redirect(reverse('verification:home'))
        rsa_handler = RsaHandler(coupon.version)
        if not rsa_handler.is_key_exist():
            messages.error(request, "没有该版本的券码校验文件")
            return redirect(reverse('verification:home'))
        rsa_handler.load_keys()
        result = rsa_handler.verify_text(coupon.coupon, coupon.signature)
        if not result:
            coupon.status = "无效"
            coupon.updated_user = request.user
            coupon.save()
            messages.error(request, "校验失败，此券码为无效券码")
            return redirect(reverse('verification:home'))
        dt = time_zone.localize(datetime.datetime.now())
        if coupon.valid_from_datetime <= dt <= coupon.expiry_datetime:
            if coupon.status == "未使用":
                coupon.status = "已使用"
                coupon.updated_user = request.user
                coupon.save()
                messages.success(request, '恭喜，兑换成功！')
                return redirect(reverse('verification:home'))
            else:
                messages.error(request, "兑换失败！券码不可用，状态为：%s" % coupon.status)
                return redirect(reverse('verification:home'))
        else:
            if dt < coupon.valid_from_datetime:
                messages.error(request, "兑换失败！该券码未生效")
                return redirect(reverse('verification:home'))
            elif dt > coupon.expiry_datetime:
                messages.error(request, "兑换失败！该券码已过期")
                return redirect(reverse('verification:home'))
    else:
        return render(request, "verification.html", {"msg_cn": "请求错误"})


def login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user:
            login_admin(request, user)
            next_url = request.META.get("HTTP_REFERER", '')
            next_url_params = parse_url_param(next_url)
            if next_url_params:
                try:
                    next_url = next_url_params['next'][0]
                    return redirect(next_url)
                except:
                    return redirect(reverse('verification:home'))
            else:
                return redirect(reverse('verification:home'))
        else:
            try:
                user = AUTH_USER_MODEL.objects.get(username=username)
                if check_password(password, user.password):
                    if user.is_active:
                        messages.error(request, "登录失败！请联系管理员")
                        return redirect(reverse('verification:login'))
                    else:
                        messages.error(request, "登录失败！该账号未启用")
                        return redirect(reverse('verification:login'))
                else:
                    messages.error(request, "登录失败！用户名或密码错误")
                    return redirect(reverse('verification:login'))
            except:
                messages.error(request, "登录失败！用户名或密码错误")
                return redirect(reverse('verification:login'))
    else:
        if request.user.is_authenticated:
            return redirect(reverse('verification:home'))
        else:
            next_url = request.GET.get('next', '')
            return render(request, 'login.html', {'next': next_url})


def logout(request):
    logout_admin(request)
    messages.success(request, "登出成功！")
    return redirect(reverse('verification:login'))
