from django.db import models
from CouponVerifier.settings import AUTH_USER_MODEL


status_choice = [("未使用", "未使用"), ("已使用", "已使用"), ("作废", "作废"), ("无效", "无效")]


class Coupon(models.Model):
    id = models.AutoField(primary_key=True)
    customer_id = models.CharField(max_length=300, verbose_name="客户id")
    coupon_type = models.CharField(max_length=30, verbose_name="券码类型")
    coupon = models.CharField(max_length=300, unique=True, verbose_name="券码")
    signature = models.CharField(max_length=1000, verbose_name="校验码")
    version = models.CharField(max_length=30, verbose_name="密钥版本")
    created_datetime = models.DateTimeField(verbose_name="创建时间")
    valid_from_datetime = models.DateTimeField(verbose_name="生效时间")
    expiry_datetime = models.DateTimeField(verbose_name="过期时间")
    status = models.CharField(max_length=30, choices=status_choice, verbose_name="状态")
    uploaded_user = models.ForeignKey(AUTH_USER_MODEL, related_name="coupon_uploaded_user", on_delete=models.DO_NOTHING, verbose_name="上传用户")
    uploaded_datetime = models.DateTimeField(auto_now_add=True, verbose_name="上传时间")
    updated_user = models.ForeignKey(AUTH_USER_MODEL, related_name="coupon_updated_user", on_delete=models.DO_NOTHING, verbose_name="最后更新用户")
    updated_datetime = models.DateTimeField(auto_now=True, verbose_name="最后更新时间")

    class Meta:
        verbose_name = "券码"
        verbose_name_plural = "券码"
        indexes = [
            models.Index(fields=['coupon'])
        ]

    def __str__(self):
        return str(self.id)


class CouponSummary(Coupon):

    class Meta:
        proxy = True
        verbose_name = "券码统计"
        verbose_name_plural = "券码统计"
