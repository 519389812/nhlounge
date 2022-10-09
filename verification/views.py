import datetime
from django.shortcuts import render, redirect, reverse
from verification.models import Coupon
from pytz import timezone
from CouponVerifier.settings import TIME_ZONE
from CouponVerifier.rsa_handler import RsaHandler
from django.contrib import messages


time_zone = timezone(TIME_ZONE)


def home(request):
    return render(request, 'verification.html')


def verify(request):
    if request.method == "POST":
        coupon_code = request.POST.get("coupon", "")
        if not coupon_code:
            return render(request, "verification.html", {"msg_cn": "请输入券码"})
        try:
            coupon = Coupon.objects.get(coupon=coupon_code)
        except:
            return render(request, "verification.html", {"msg_cn": "未找到该券码", "coupon": coupon_code})
        rsa_handler = RsaHandler(coupon.version)
        if not rsa_handler.is_key_exist():
            return render(request, "verification.html", {"msg_cn": "没有该版本的券码校验文件", "coupon": coupon_code})
        rsa_handler.load_keys()
        result = rsa_handler.verify_text(coupon.coupon, coupon.signature)
        if not result:
            coupon.status = "无效"
            coupon.save()
            return render(request, "verification.html", {"msg_cn": "校验失败，此券码为无效券码", "coupon": coupon_code})
        dt = time_zone.localize(datetime.datetime.now())
        if coupon.valid_from_datetime <= dt <= coupon.expiry_datetime:
            if coupon.status == "未使用":
                coupon.status = "已使用"
                coupon.save()
                messages.success(request, '恭喜，兑换成功！')
                return redirect(reverse('verification:home'))
            else:
                return render(request, "verification.html", {"msg_cn": "兑换失败！券码不可用，状态为：%s" % coupon.status, "coupon": coupon_code})
        else:
            if dt < coupon.valid_from_datetime:
                return render(request, "verification.html", {"msg_cn": "兑换失败！该券码未生效", "coupon": coupon_code})
            elif dt > coupon.expiry_datetime:
                return render(request, "verification.html", {"msg_cn": "兑换失败！该券码已过期", "coupon": coupon_code})
    else:
        return render(request, "verification.html", {"msg_cn": "请求错误"})


