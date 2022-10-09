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
            coupon.save()
            messages.error(request, "校验失败，此券码为无效券码")
            return redirect(reverse('verification:home'))
        dt = time_zone.localize(datetime.datetime.now())
        if coupon.valid_from_datetime <= dt <= coupon.expiry_datetime:
            if coupon.status == "未使用":
                coupon.status = "已使用"
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


