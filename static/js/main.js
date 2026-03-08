// static/js/main.js - 全局JavaScript功能

$(document).ready(function() {
    // 初始化工具提示
    $('[data-bs-toggle="tooltip"]').tooltip();

    // 自动隐藏警告消息
    setTimeout(function() {
        $('.alert').fadeOut('slow');
    }, 5000);

    // 表单验证增强
    $('form').on('submit', function() {
        var $form = $(this);
        var $submitBtn = $form.find('button[type="submit"]');

        // 禁用提交按钮防止重复提交
        $submitBtn.prop('disabled', true).html('<i class="fas fa-spinner fa-spin"></i> 处理中...');
    });

    // 数字输入框格式化
    $('input[type="number"]').on('blur', function() {
        var value = parseFloat($(this).val());
        if (!isNaN(value)) {
            $(this).val(value.toFixed(2));
        }
    });
});

// 全局函数：显示加载动画
function showLoading(message) {
    if (!$('#loadingOverlay').length) {
        var overlay = $('<div id="loadingOverlay" style="position:fixed;top:0;left:0;width:100%;height:100%;background:rgba(0,0,0,0.5);z-index:9999;display:flex;align-items:center;justify-content:center;">' +
                       '<div class="spinner-border text-primary" role="status" style="width:3rem;height:3rem;">' +
                       '<span class="visually-hidden">加载中...</span></div>' +
                       '<span class="text-white ms-3">' + (message || '处理中...') + '</span></div>');
        $('body').append(overlay);
    }
}

// 全局函数：隐藏加载动画
function hideLoading() {
    $('#loadingOverlay').remove();
}

// AJAX全局设置
$.ajaxSetup({
    beforeSend: function() {
        showLoading();
    },
    complete: function() {
        hideLoading();
    },
    error: function(xhr, status, error) {
        console.error('AJAX错误:', status, error);
        alert('请求失败，请检查网络连接或联系管理员。错误: ' + error);
    }
});

// 导出为Excel（通用函数）
function exportToExcel(tableId, filename) {
    var table = document.getElementById(tableId);
    var html = table.outerHTML;

    // 创建Blob对象
    var blob = new Blob([html], { type: 'application/vnd.ms-excel' });

    // 创建下载链接
    var link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = filename || 'export.xls';
    link.style.display = 'none';

    // 添加到页面并触发下载
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// 计算人工数（通用函数）
function calculateLabor(coefficient, quantity) {
    return parseFloat((coefficient * quantity).toFixed(2));
}

// 格式化日期
function formatDate(date, format) {
    var d = date ? new Date(date) : new Date();
    var year = d.getFullYear();
    var month = ('0' + (d.getMonth() + 1)).slice(-2);
    var day = ('0' + d.getDate()).slice(-2);
    var hours = ('0' + d.getHours()).slice(-2);
    var minutes = ('0' + d.getMinutes()).slice(-2);
    var seconds = ('0' + d.getSeconds()).slice(-2);

    format = format || 'YYYY-MM-DD HH:mm:ss';

    return format
        .replace('YYYY', year)
        .replace('MM', month)
        .replace('DD', day)
        .replace('HH', hours)
        .replace('mm', minutes)
        .replace('ss', seconds);
}

