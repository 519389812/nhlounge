import io
import os.path
import re
from django.contrib import admin
from django.http import HttpResponse, JsonResponse, HttpResponseRedirect
from django.shortcuts import render
from django.template.response import TemplateResponse
from django.contrib import messages
from verification.models import Coupon, CouponSummary
from io import BytesIO
import datetime
import numpy as np
import pandas as pd
from simpleui.admin import AjaxAdmin
from pytz import timezone as pytz_timezone
from CouponVerifier.settings import TIME_ZONE, KEY_DIR, BASE_DIR
from django.utils.html import format_html


time_zone = pytz_timezone(TIME_ZONE)

upload_columns = ["客户id", "券码类型", "券码", "校验码", "密钥版本", "创建时间", "生效时间", "过期时间", "状态"]


class CouponAdmin(AjaxAdmin):
    fieldsets = (
        ('客户', {'fields': ('id', 'customer_id')}),
        ('券码', {'fields': ('coupon_type', 'coupon', 'signature')}),
        ('券码描述', {'fields': ('version', 'created_datetime', 'valid_from_datetime', 'expiry_datetime')}),
        ('状态', {'fields': ('status', 'is_valid')}),
        ('操作', {'fields': ('uploaded_user', 'uploaded_datetime', 'updated_user', 'updated_datetime')}),
    )
    list_display = ('id', 'customer_id', 'coupon_type', 'coupon', 'version', 'valid_from_datetime', 'expiry_datetime',
                    'status', 'is_valid', 'updated_user', 'updated_datetime')
    list_editable = ('status', )
    readonly_fields = ('id', 'customer_id', 'coupon_type', 'coupon', 'signature', 'version', 'created_datetime',
                       'valid_from_datetime', 'expiry_datetime', 'is_valid', 'uploaded_user', 'uploaded_datetime',
                       'updated_user', 'updated_datetime')
    list_filter = ('created_datetime', 'valid_from_datetime', 'expiry_datetime')
    # filter_horizontal = ('many_to_many_field')
    # autocomplete_fields = ['']
    search_fields = ('coupon', 'customer_id')
    actions = ['export_directly', 'upload_coupon', 'upload_key']

    def save_model(self, request, obj, form, change):
        if form.is_valid():
            obj.updated_user = request.user
            super().save_model(request, obj, form, change)

    def is_valid(self, obj):
        try:
            now_datetime = time_zone.localize(datetime.datetime.now())
            if obj.valid_from_datetime <= now_datetime <= obj.expiry_datetime:
                is_valid = "是"
                color = 'green'
            else:
                is_valid = "否"
                color = 'red'
        except:
            is_valid = "否"
            color = 'red'
        return format_html('<p style="color:{};">{}</p>', color, is_valid)
    is_valid.short_description = "有效期内"

    def export_directly(self, request, queryset):
        outfile = BytesIO()
        data = pd.DataFrame(
            queryset.values('id', 'customer_id', 'coupon_type', 'coupon', 'signature', 'version', 'created_datetime',
                            'valid_from_datetime', 'expiry_datetime', 'status', 'uploaded_user__username',
                            'uploaded_datetime', 'updated_user__username', 'updated_datetime'))
        data = data.rename(columns={'id': '序号', 'customer_id': '客户id', 'coupon_type': '券码类型', 'coupon': '券码',
                                    'signature': '校验码', 'version': '密钥版本', 'created_datetime': '创建时间',
                                    'valid_from_datetime': '生效时间', 'expiry_datetime': '过期时间', 'status': '状态',
                                    'uploaded_user__username': '上传用户', 'uploaded_datetime': '上传时间',
                                    'updated_user__username': '最后更新用户', 'updated_datetime': '最后更新时间'})
        data['创建时间'] = (data['创建时间'] + datetime.timedelta(hours=8)).dt.strftime('%Y-%m-%d %H:%M:%S')
        data['生效时间'] = (data['生效时间'] + datetime.timedelta(hours=8)).dt.strftime('%Y-%m-%d %H:%M:%S')
        data['过期时间'] = (data['过期时间'] + datetime.timedelta(hours=8)).dt.strftime('%Y-%m-%d %H:%M:%S')
        data['上传时间'] = (data['上传时间'] + datetime.timedelta(hours=8)).dt.strftime('%Y-%m-%d %H:%M:%S')
        data['最后更新时间'] = (data['最后更新时间'] + datetime.timedelta(hours=8)).dt.strftime('%Y-%m-%d %H:%M:%S')
        data = data.sort_values(by=['序号'], ascending=True)
        data = data.fillna('')
        filename = 'Coupon_' + datetime.datetime.now().strftime('%Y-%m-%d_%H%M%S') + '.xlsx'
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = "attachment;filename={}".format(filename)
        data.to_excel(outfile, index=False)
        response.write(outfile.getvalue())
        return response
    export_directly.short_description = "直接导出"
    # export_directly.icon = "fa-regular fa-download"
    export_directly.type = "warning"
    # export_directly.style = "color:black;"
    # export_directly.confirm = "是否确认"
    # export_directly.action_type = 0  # 0当前页 1新tab 2浏览器tab

    def upload_coupon(self, request, queryset):
        if request.method == "POST":
            try:
                file = request.FILES['uploaded']
            except:
                return JsonResponse(data={"status": "error", "msg": "没有接收到文件"})
            try:
                file_type = file.name.split('.')[1]
            except:
                file_type = ""
            if file_type != 'xlsx':
                return JsonResponse(data={"status": "error", "msg": "文件格式错误"})
            data = pd.read_excel(file, converters={"客户id": str, "券码类型": str, "券码": str, "校验码": str, "创建时间": str, "生效时间": str, "过期时间": str})
            for c in upload_columns:
                if c not in data.columns:
                    return JsonResponse(data={"status": "error", "msg": "文件内容格式错误"})
            missed = []
            for i, r in data.iterrows():
                try:
                    Coupon.objects.create(customer_id=r['客户id'], coupon_type=r['券码类型'], coupon=r['券码'],
                                          signature=r['校验码'], version=r['密钥版本'], created_datetime=r['创建时间'],
                                          valid_from_datetime=r['生效时间'], expiry_datetime=r['过期时间'],
                                          status=r['状态'], uploaded_user=request.user, updated_user=request.user)
                except:
                    missed.append(r['券码'])
            if missed:
                self.message_user(request, "券码：%s 上传失败" % ','.join(missed), messages.INFO)
                return JsonResponse(data={"status": "success", "msg": "券码上传完成，部分券码上传失败"})
            return JsonResponse(data={"status": "success", "msg": "全部券码上传成功"})
    upload_coupon.short_description = '上传券码'
    upload_coupon.type = "warning"
    upload_coupon.layer = {
        "title": "上传券码",
        "tips": "请选择上传文件，文件格式为.xlsx",
        "confirm_button": "确认上传",
        "cancel_button": "取消",
        "width": "50%",
        "labelWidth": "80px",
        # size small/medium/mini  options: [{"key": "0", "label": "..."}, ]  "value": ""  "width": "200px", "size": "small"
        "params": [{"type": "file", "key": "uploaded", "label": "文件"}],
    }

    def upload_key(self, request, queryset):
        if request.method == "POST":
            try:
                file = request.FILES['uploaded']
            except:
                return JsonResponse(data={"status": "error", "msg": "没有接收到文件"})
            p = re.compile('^public_key_v\d+.pem')
            if not p.match(file.name):
                return JsonResponse(data={"status": "error", "msg": "文件名称或格式错误"})
            if file.size > 2000:
                return JsonResponse(data={"status": "error", "msg": "文件过大"})
            try:
                with open(os.path.join(BASE_DIR, KEY_DIR, file.name), 'wb') as f:
                    # for chunk in file.chunks():
                    #     f.write(chunk)
                    f.write(file.read())
            except:
                return JsonResponse(data={"status": "error", "msg": "写入文件失败"})
            return JsonResponse(data={"status": "success", "msg": "导入成功"})
    upload_key.short_description = '上传密钥'
    upload_key.type = "warning"
    upload_key.layer = {
        "title": "上传密钥",
        "tips": "请选择上传密钥文件，并确保密钥文件名称以public_key_v{版本号}.pem的格式命名",
        "confirm_button": "确认上传",
        "cancel_button": "取消",
        "width": "50%",
        "labelWidth": "80px",
        # size small/medium/mini  options: [{"key": "0", "label": "..."}, ]  "value": ""  "width": "200px", "size": "small"
        "params": [{"type": "file", "key": "uploaded", "label": "文件"}],
    }


class CouponSummaryAdmin(admin.ModelAdmin):
    change_list_template = "admin/coupon_summary_change_list.html"

    search_fields = ('customer_id', )
    list_filter = ('created_datetime', 'valid_from_datetime', 'expiry_datetime')

    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context=extra_context)
        try:
            qs = response.context_data['cl'].queryset
        except (AttributeError, KeyError):
            return response
        qs = pd.DataFrame(qs.values('customer_id', 'status', 'valid_from_datetime', 'expiry_datetime'))
        if qs.shape[0] > 0:
            qs.rename(columns={'customer_id': '客户id', 'status': '状态', 'valid_from_datetime': '生效时间', 'expiry_datetime': '过期时间'}, inplace=True)
            qs.fillna('', inplace=True)
            dt = time_zone.localize(datetime.datetime.now())
            # qs['生效时间'] = qs['生效时间'].apply(lambda x: time_zone.localize(x))
            # qs['过期时间'] = qs['过期时间'].apply(lambda x: time_zone.localize(x))
            qs.loc[qs[qs['生效时间'] > dt].index, '状态'] = '未生效'
            qs.loc[qs[qs['过期时间'] < dt].index, '状态'] = '已过期'
            qs = qs[['客户id', '状态']]
            qs['状态2'] = qs['状态']
            # margins 必须加dropna=False参数才能生效
            qs = pd.pivot_table(qs, index=['客户id'], values=['状态2'], columns=['状态'], fill_value=0, margins=True, margins_name='总计', aggfunc=np.count_nonzero)
            qs.columns = [c[1] for c in qs.columns]
            qs.fillna(0, inplace=True)
            qs = qs.astype(int)
            # cols = qs.columns.tolist()
            # cols.sort()
            # qs = qs[cols]
            # qs = qs.round(2)
            # qs['总计'] = qs.sum(axis=1)
            response.context_data['summary'] = qs
        return response


admin.site.register(Coupon, CouponAdmin)
admin.site.register(CouponSummary, CouponSummaryAdmin)

admin.site.site_header = '券码核销系统'
admin.site.site_title = '券码核销系统'
admin.site.index_title = '券码核销系统'
