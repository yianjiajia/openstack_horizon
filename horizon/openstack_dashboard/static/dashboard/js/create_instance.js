/**
 * Created by zhihao.ding 2015/10/26
 */

g_is_init_quotas = false;
g_select_image_min_disk = 0;
g_is_allow_inject_passwd = 0;

function get_real_url() {
    var url = window.location.pathname;
    var real_url;
    if (url.split("/")[1] == 'dashboard'){
        real_url = "/dashboard";
    } else {
        real_url = "";
    }
    return real_url;
}

function is_have_select_image_page() {
    return ($("#launch_instance__selectimage").length >= 1);
}

function get_current_page_number() {
    var current_page_number = 1;
    var counter = 1;
    $(".create_instance .line-content.wizard-tabs").find('li').each(function(){
        if ($(this).hasClass('active')) {
            current_page_number = counter;
        }
        counter += 1;
    });
    if (!is_have_select_image_page()) {
        current_page_number += 1;
    }
    return current_page_number;
}

function close_msg() {

    function _close_msg_for_page_1() {
        $("#id_show_error_msg_for_page_1").remove();
    }

    function _close_msg_for_page_2() {
        $("#id_show_error_msg_for_page_2").remove();
    }

    function _close_msg_for_page_3() {
        $("#id_show_error_msg_for_page_3").remove();
    }

    switch (get_current_page_number()) {
        case 1:{
            _close_msg_for_page_1();
            break;
        }
        case 2:{
            _close_msg_for_page_2();
            break;
        }
        case 3:
        default:{
            _close_msg_for_page_3();
            break;
        }
    }
}

function do_msg(assert, err_message) {

    function _do_msg_for_page_1(err_message) {
        $("#id_show_error_msg_for_page_1").remove();
        var err_div = '<div id="id_show_error_msg_for_page_1" class="alert alert-message alert-danger">' +
                  '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                  '<ul class="errorlist nonfield"><li>' +
                  err_message + '</li></ul></div>';
        $("#launch_instance__selectimage #instance-config").prepend(err_div);
    }

    function _do_msg_for_page_2(err_message) {
        $("#id_show_error_msg_for_page_2").remove();
        var err_div = '<div id="id_show_error_msg_for_page_2" class="alert alert-message alert-danger">' +
                  '<button type="button" class="close" data-dismiss="alert">&times;</button>' +
                  '<ul class="errorlist nonfield"><li>' +
                  err_message + '</li></ul></div>';
        $("#launch_instance__selectconfig #instance-config").prepend(err_div);
    }

    function _do_msg_for_page_3(err_message) {
        $("#id_show_error_msg_for_page_3").remove();
        var err_div = '<div id="id_show_error_msg_for_page_3" class="alert alert-message alert-danger">' +
                      '<button type="button" class="close" data-dismiss="alert">&times;</button>' + 
                      '<ul class="errorlist nonfield"><li>' +
                      err_message + '</li></ul></div>';
        $("#launch_instance__baseinfo #instance-config").prepend(err_div);
    }

    if (assert) return assert;
    switch (get_current_page_number()) {
    case 1:
        return _do_msg_for_page_1(err_message);
    case 2:
        return _do_msg_for_page_2(err_message);
    case 3:
    default:
        return _do_msg_for_page_3(err_message);
    }
    return false;
}

function disable_final_btn() {
    $('.next .button-final').attr('disabled','true');
}

function enable_final_btn() {
    $('.next .button-final').removeAttr('disabled');
}

// check all
function check_all() {

    function _is_create_data_volume() {
        return (parseInt($("#amount").val()) > 0);
    }

    function _is_create_floating_ip() {
        return ($('#id_is_create_floating_ip').attr('checked'));
    }

    // check network
    function _check_network() {
        var value = $("#id_network").val();
        return do_msg(value, '网络环境未搭建完成，请确认路由器，网络，内网接口是否创建！');
    }

    // check vcpus
    function _check_vcpus(instance_count) {
        var available_cores = parseInt($('#id_cloud_hdd').attr('vcpus_avl'));
        var vcpus = parseInt($("#id_vcpus").val());
        return do_msg((instance_count * vcpus <= available_cores),
                   'CPU超过配额(CPU:'+vcpus+',服务器数:'+instance_count+'),目前所剩配额为'+available_cores+'核!');
    }

    // check ram
    function _check_ram(instance_count) {
        var available_ram = parseInt($('#id_cloud_hdd').attr('mem_avl'));
        var mem = parseInt($("#id_memory_mb").val());
        return do_msg((instance_count * mem <= available_ram),
                   '内存超过配额(内存:'+mem+',服务器数:'+instance_count+'),目前所剩配额为'+available_ram+'MB!');
    }

    // check volume count
    function _check_volume_count(instance_count) {
        var available_vol_count = parseInt($('#id_cloud_hdd').attr('hdd_count_avl'));
        var will_create_volume_count = 1;
        if (_is_create_data_volume()) {
            will_create_volume_count += 1;
        }
        return do_msg((will_create_volume_count * instance_count <= available_vol_count), 
                      '云硬盘数量超过配额(硬盘数:'+will_create_volume_count+',服务器数:'+instance_count+'),目前所剩配额为'+available_vol_count+'块!');
    }

    // check boot volume size
    function _check_boot_volume_size(instance_count) {
        var hdd_avl = parseInt($('#id_cloud_hdd').attr('hdd_avl'));
        var min_disk = parseInt(g_select_image_min_disk);
        return do_msg((min_disk * instance_count <= hdd_avl),
                      "磁盘配额不足！(镜像大小:"+min_disk+"G,服务器数:"+instance_count+"),剩余配额:"+hdd_avl+'个!');
    }

    // check data volume size
    function _check_data_volume_size(instance_count) {
        var hdd_avl = parseInt($('#id_cloud_hdd').attr('hdd_avl'));
        var min_disk = parseInt(g_select_image_min_disk);
        var data_disk_size = parseInt($('#amount').val());
        if (_is_create_data_volume()) {
            return do_msg(((min_disk+data_disk_size)*instance_count <= hdd_avl), 
                          "磁盘配额不足！(镜像大小:"+(min_disk+data_disk_size)+"G,服务器数:"+instance_count+"), 剩余配额:"+hdd_avl+"G")
        }
        return true;
    }

    // check floating ip count
    function _check_floating_ip_count(instance_count) {
        var available_float_ip = parseInt($('#id_cloud_hdd').attr('float_ip_avl'));
        if (_is_create_floating_ip()) {
            return do_msg((instance_count <= available_float_ip), "浮动IP不足！（剩余配额:"+available_float_ip+",服务器数:"+instance_count+"）");
        }
        return true;
    }

    if (!g_is_init_quotas) return false;

    var is_check_pass = false;
    var instance_count = parseInt($('#id_count').val());
    if (''+instance_count+'' == 'NaN') {
        instance_count = 0;
    }
    do
    {
        if (!_check_network()) break;
        if (!_check_vcpus(instance_count)) break;
        if (!_check_ram(instance_count)) break;
        if (!_check_volume_count(instance_count)) break;
        if (!_check_boot_volume_size(instance_count)) break;
        if (!_check_data_volume_size(instance_count)) break;
        if (!_check_floating_ip_count(instance_count)) break;
        close_msg();
        is_check_pass = true;
    }while(0);
    if (is_check_pass) {
        enable_final_btn();
    } else {
        disable_final_btn();
    }
    return is_check_pass;
}

// validate all
function validate_all() {
    // is chinese char
    function _is_chinese_char(str) {
        var re=/[\u4E00-\u9FA5\uF900-\uFA2D]/;
        return re.test(str);
    }

    // is full width char
    function _is_fullwidth_char(str) {
        var re=/[\uFF00-\uFFEF]/;
        return re.test(str);
    }

    // validate instance name
    function _validate_instance_name(name) {
        return do_msg((name.length > 0), "云服务器名称不能为空！");
    }

    // validate instance count
    function _validate_instance_count(count) {
        return do_msg((parseInt(count) > 0), "至少创建1个云服务器！");
    }

    // validate username rules
    function _validate_username_rules(username) {
        var re=/^[^/\\\[\]"":;|<>+=,?*]*$/;
        return re.test(username);
    }

    // validate instance username
    function  _validate_instance_username(username) {
        if (!g_is_allow_inject_passwd) return true;
        return do_msg((username.length > 0), "请输入实例登陆的用户名！") &&
               do_msg((username != 'root' && username != 'Administrator'), "root/Administrator为系统用户，请设置其他用户名！") &&
               do_msg(_validate_username_rules(username), "输入用户名无效！不能包含以下字符:/\\[]\":;|<>+=,?*") &&
               do_msg(!_is_chinese_char(username) && !_is_fullwidth_char(username), "输入用户名无效！不能包含中文字符！");
    }

    // validate password rules
    function _validate_password_rules(password) {
        var re=/^(?=.*^[a-zA-Z])(?=.*\d)(?=.*[~!@#$%^&*()_+`\-={}:";\'<>?,.\/]).{8,64}$/g;
        return re.test(password);
    }

    // validate instance password
    function _validate_instance_password(passowrd, confirm_password) {
        if (!g_is_allow_inject_passwd) return true;
        return do_msg((passowrd.length > 0 && confirm_password.length > 0), "请输入密码！") &&
               do_msg((passowrd == confirm_password), "两次输入密码不同！") &&
               do_msg(_validate_password_rules(passowrd), "密码必须以字母开头，8-64位，同时包括字母、数字和符号!");
    }

    if (!g_is_init_quotas) return false;

    var instance_name = $("#id_name").val();
    var instance_count = $("#id_count").val();
    var username = $("#id_username").val();
    var password = $("#id_admin_pass").val();
    var confirm_password = $("#id_confirm_admin_pass").val();

    var is_validate_pass = false;
    do
    {
        if (!_validate_instance_name(instance_name)) break;
        if (!_validate_instance_count(instance_count)) break;
        if (!_validate_instance_username(username)) break;
        if (!_validate_instance_password(password, confirm_password)) break;
        close_msg();
        is_validate_pass = true;
    } while(0);
    return is_validate_pass;
}

// init next btn
function init_next_btn() {
    $(".button-next").click(function() {
        return check_all();
    }); 
}

// init final btn 
function init_final_btn() {
    $(".button-final").click(function() {
        return check_all() && validate_all();
    });
}

// init instance count input
function init_instance_count_input() {
    $("#id_count").on('click', function() {
        var count = $(this).val();
        $(".flavor_count,#flavor_count").each(function(){
            $(this).text(count);
        });
        check_all();
        get_price();
    });
    $("#id_count").on('keyup', function() {
        var count = $(this).val();
        $(".flavor_count,#flavor_count").each(function(){
            $(this).text(count);
        });
        check_all();
        get_price();
    });
}

// init data volume slider and input
function init_data_volume_slider_and_input() {
    $("#slider-range-max").slider({
        range: "min",
        min: 0,
        max: 2000,
        value: 0,
        slide: function(event, ui) {
            $("#amount").val(ui.value);
            $("#id_cloud_hdd").val(ui.value);
            $(".flavor_cloud_drive,#flavor_cloud_drive").text(ui.value);
            check_all();
            get_price();
        }
    });

    $("#amount").val($("#slider-range-max").slider("value"));
    $("#id_cloud_hdd").val($("#slider-range-max").slider("value"));
    $(".flavor_cloud_drive,#flavor_cloud_drive").text($("#slider-range-max").slider("value"));

    $("#amount").keyup(function() {
        var data_volume_size = parseInt($(this).val()); // 取整
        if (''+data_volume_size+'' == 'NaN') {
            data_volume_size = 0;
        }
        $("#amount").val(data_volume_size);
        $("#id_cloud_hdd").val(data_volume_size);
        $(".flavor_cloud_drive,#flavor_cloud_drive").text(data_volume_size);
        $("#slider-range-max").slider({
          range: "min",
          min: 0,
          max: 2000,
          value: data_volume_size
        });
        check_all();
        get_price();
    });

    $("#amount").click(function() {
        var data_volume_size = parseInt($(this).val()); // 取整
        if (''+data_volume_size+'' == 'NaN') {
            data_volume_size = 0;
        }
        $("#amount").val(data_volume_size);
        $("#id_cloud_hdd").val(data_volume_size);
        $(".flavor_cloud_drive,#flavor_cloud_drive").text(data_volume_size);
        $("#slider-range-max").slider({
          range: "min",
          min: 0,
          max: 2000,
          value: data_volume_size
        });
        check_all();
        get_price();
    });
}

// init floating ip input
function init_floating_ip_input() {
    $(".form-group.floating_ip_limit_speed").hide();
    $("#id_is_create_floating_ip").on('click', function(){
        if ($(this).attr("checked")) {
            $(".form-group.floating_ip_limit_speed").show();
            $(".floating_ip,#floating_ip").text('1');
        } else {
            $(".form-group.floating_ip_limit_speed").hide();
            $(".floating_ip,#floating_ip").text('0');
        }
        check_all();
        get_price();
    });
}

// init script input
function init_script_input() {
    $("#id_script_data").hide();
    $("#id_script_upload").hide();
    $("#id_script_upload").parent().parent().find(".control-label").hide();
    $("#id_script_data").parent().parent().find(".control-label").hide();

    //select 替换成  radio
    /*
    str='<div class="controls">' +
    '<label class="inline"><input type="radio" value="" name="script_source" checked="checked">无</label>'+
    '<label class="inline"><input type="radio" value="raw" name="script_source">文本输入</label>' +
    '<label class="inline"><input type="radio" value="file" name="script_source">文件上传</label>' +
    '</div>';
    $("#id_script_source").parent().html(str);
    */
    $("#launch_instance__baseinfo #instance-config .script_source").html("");
    $(".controls input").live('click',function(){
        val=$('input:radio:checked').val();
        $("#id_script_data").hide();
        $("#id_script_upload").hide();

        if(val=="raw"){
            $("#id_script_data").show();
        }
        if(val=="file"){
            $("#id_script_upload").show();
        }

        if(val=='no'){
            $("#id_script_upload").parent().parent().find(".control-label").hide();
            $("#id_script_data").parent().parent().find(".control-label").hide();
        }
    });
}

// init flavor table
function init_flavor_table() {
    var cpu = $("#id_vcpus").find("option:selected").text();
    $(".table.flavor_table span.flavor_vcpus").each(function(){
        $(this).html(cpu);
    });
    
    var mem = $("#id_memory_mb").find("option:selected").text();
    $(".flavor_ram,#flavor_ram").each(function(){
        $(this).text(mem);
    });

    var count = $("#id_count").val();
    $(".flavor_count,#flavor_count").each(function(){
        $(this).text(count);
    $(".floating_ip,#floating_ip").text('0');
    });
}

function _hide_inject_items(is_allow_inject_passwd) {
    $("#launch_instance__baseinfo .form-group").slice(2).each(function(index){
        if (is_allow_inject_passwd) {
            $(this).show();
            if (parseInt(index) == 2 || parseInt(index) == 3) {
                $(this).addClass('required');
            }
        } else {
            $(this).hide();
        }
        g_is_allow_inject_passwd = is_allow_inject_passwd;
    });

    if (is_allow_inject_passwd) {
        $("#id_admin_pass").removeAttr("disabled");
        $("#id_confirm_admin_pass").removeAttr("disabled");
    } else {
        $("#id_admin_pass").attr("disabled", "disabled");
        $("#id_confirm_admin_pass").attr("disabled", "disabled");
    }
}

function get_image_info(image_id) {
    $.get(get_real_url()+"/instances/api?image_id="+image_id,function(data){
        data_json = eval('(' + data + ')');
        $(".flavor_system_drive,#flavor_system_drive").text(data_json.min_disk+"G");
        init_price();
        _hide_inject_items(data_json.is_allow_inject_passwd);
        g_select_image_min_disk = parseInt(data_json.min_disk);
        check_all();
    });
}

// init select public image
function init_select_public_image_option() {
    $("#id_selectimage_role_image_id option").eq(1).attr("selected", true);
    $(".available_members .nav").eq(0).addClass('selected');

    var init_image = $(".available_members .nav").eq(0).find("li:first").text();
    get_image_tooltip(init_image);

    $("#id_selectimage_role_image_id option").each(function(){
        if(init_image === $(this).text()){
            image_id = $(this).val();
            get_image_info(image_id);
            $("#id_custom_image option").removeAttr("selected");
            $("#id_selectimage_role_image_id option").removeAttr("selected");
            $(this).attr("selected", true);
        }
    });

    $(".available_members .nav").on('click',function(){
        $("#custom_image").children().find("li").removeClass("selected");
        $(".nav").removeClass("selected");
        $(this).addClass('selected');

        var image_attr = $(this).find("li:first").attr('data-selectimage-id').split('_');
        var image_id = image_attr[image_attr.length-1];
        var value = $(this).find("li:first").text();
        get_image_tooltip(value);
        $("#id_selectimage_role_image_id option").each(function(){
            if(image_id === $(this).val()){
                image_id = $(this).val();
                get_image_info(image_id);
                $("#id_custom_image option").removeAttr("selected");
                $("#id_selectimage_role_image_id option").removeAttr("selected");
                $(this).attr("selected", true);
            }
        });
    });
}

// init image filter
function init_image_filter() {
    $(".available_members .nav").find("li:first").each(function(){
        select_image = $(this).text().split('-')[0];
        if (select_image !== "CentOS") {
          $(this).parent().hide();
        }
        if (select_image == "CentOS"){
          $(this).parent().show();
        }
    });

    $('#other').on('click', function(){
        $(".provider.system-provider-sys .provider-filter").removeClass('active');
        $(this).parent().addClass('active');
        $(".available_members .nav").hide();
        $(".available_members .nav").find("li:first").each(function(){
            select_image = $(this).text().split('-')[0];
            if (select_image){ 
                $("#no_available_selectimage").hide()
            }
            if(select_image !== 'CentOS' &&
               select_image !== 'Debian' &&
               select_image !== 'Ubuntu' &&
               select_image !== 'SUSE' &&
               select_image !== 'RHEL' &&
               select_image !== 'Windows') {
                  $(this).parent().show();
            }
        });
    });

    $(".provider.system-provider-sys .provider-filter").on("click",function(){
        var num = 0;
        $(".provider.system-provider-sys .provider-filter").removeClass('active');
        $(this).addClass('active');
        var image_name = $(this).attr("data-val");
        if (image_name !== 'other'){
            $(".available_members .nav").find("li:first").each(function(){
                select_image = $(this).text().split('-')[0];
                $("#no_available_selectimage").hide();
                if (select_image !== image_name){
                    $(this).parent().hide();
                }
                if (select_image == image_name){
                    num = num + 1;
                    $(this).parent().show();
                }
                if(num == 0){
                    $("#no_available_selectimage").show();
                }
            });
        }
    });
}

// init image filter for public custom
function init_image_filter_for_public_custom() {
    $(".all-provider .provider-filter").on("click",function() {
        if($(this).find("#custom").hasClass("label-warning")) {
            return false;
        }
        image_type = $(this).attr("data-val");
        if (image_type == "public") {
            $("#custom").removeClass("label-warning").addClass("label-default");
            $("#public").addClass("label-warning").removeClass("label-default");
            $(".provider.system-provider-sys").show();
            $("#available_selectimage").show();
            $("#custom_image").hide();
        } else {
            $("#custom").addClass("label-warning").removeClass("label-default");
            $("#public").removeClass("label-warning").addClass("label-default");
            if(!$("#custom_image .list-group").children().hasClass("selected")) {
                $.getJSON(get_real_url()+"/instances/api?"+'callback=?', function(data) {
                    ul = '<ul class="list-group">';
                    for(var i=0;i<data.length;i++){
                        ul += '<li class="list-group-item" data-selectimage-id='+data[i][0]+'>'+data[i][1]+'</li>';
                        if($("#id_selectimage_role_image_id option:contains("+data[i][1]+")").length < 1) {
                            $("#id_selectimage_role_image_id").append("<option value="+data[i][0]+">"+data[i][1]+"</option>");
                        }
                    }
                    if(data.length) { 
                        $("#custom_image").html(ul+'</ul>');
                    } else {
                        $("#custom_image").html("<div><ul id='no_available' style='margin: 0 0 7px 100px;'>" + 
                                                "<li>无自定义镜像</li></ul></div>");
                    }
                });
            }
            $(".provider.system-provider-sys").hide();
            $("#available_selectimage").hide();
            $("#custom_image").show();
        }
    });

    $(".list-group li").live("click",function() {
        $(".list-group li").removeClass("selected");
        $(".nav").removeClass("selected");
        $(this).addClass('selected');
        var image_name = $(this).text();
        var image_id = $(this).attr('data-selectimage-id');
        get_image_tooltip(image_name);
        $("#id_custom_image option").each(function() {
            if(image_id == $(this).val()) {
                image_id = $(this).val();
                get_image_info(image_id);
                $("#id_custom_image option").removeAttr("selected");
                $("#id_selectimage_role_image_id option").removeAttr("selected");
                $(this).attr("selected", true);
            }
        });
    });
}

// init volume and snap info
function init_volume_and_snap_info() {
    $("#image").hide();
    if (is_have_select_image_page()) return;
    var size = $("#id_image_name").attr('size');
    var is_allow_inject_passwd = parseInt($("#id_image_name").attr('is_allow_inject_passwd'));
    var image_name = $("#id_image_name").val();
    if (size) {
        $("#image").show();
        $("#image_name").text(image_name);
        get_image_tooltip(image_name);
        $(".flavor_system_drive").text(size + 'G');
        init_price();
        g_select_image_min_disk = parseInt(size);
    }
    _hide_inject_items(is_allow_inject_passwd);
}

// init select cpu and memory btn
function init_select_cpu_and_memory_option() {

    $("#id_vcpus option").each(function(){
        var value = $(this).val();
        var text = $(this).html();
        var selected = ($(this).attr("selected") == "selected");
        var insert_html = "<div data-value=\"" + value + "\" class=\"types-options cpu-options "
                + (selected ? "selected" : "") + "\" style=\"width: 53px;height:35px; padding:3px\">" + text + "核</div>";
        $(".cpu .options").append(insert_html);
    });

    $("#id_memory_mb option").each(function(){
        var value = $(this).val();
        var text = $(this).html();
        var selected = ($(this).attr("selected") == "selected");
        var insert_html = "<div data-value=\"" + value + "\" class=\"types-options memory-options "
                + (selected ? "selected" : "") + "\" style=\"width: 53px; height:35px; padding:3px; margin-top: 12px;\">" + text + "</div>";
        $(".memory .options").append(insert_html);
    });

    //select cpu
    $(".cpu .options .types-options").on('click',function(){
        var available_cores = parseInt($('#id_cloud_hdd').attr('vcpus_avl'));
        var available_ram = parseInt($('#id_cloud_hdd').attr('mem_avl'));

        $(".cpu .options .types-options").removeClass("selected");
        $(this).addClass('selected');
        
        var cpu_value = $(this).attr("data-value");
        var memory = parseInt($('#id_memory_mb').val());
        $(".flavor_vcpus,#flavor_vcpus").each(function(){
            $(this).html(cpu_value);
        });
        $("#id_vcpus option").each(function(){
            if(cpu_value === $(this).val()){
                $("#id_vcpus option").removeAttr("selected");
                $(this).attr("selected", true);
            }
        });
        check_all();
        get_price();
    });
    //select memory
    $(".memory .options .types-options").on('click',function(){
        var available_cores = parseInt($('#id_cloud_hdd').attr('vcpus_avl'));
        var available_ram = parseInt($('#id_cloud_hdd').attr('mem_avl'));
        $(".memory .options .types-options").removeClass("selected");
        $(this).addClass('selected');

        var mem_value = $(this).attr("data-value");
        var clean_data = $(this).text();
        var vcpu = parseInt($('#id_vcpus').find('option:selected').val());
        var i_count = parseInt($('#id_count').val());
        $(".flavor_ram,#flavor_ram").each(function(){
            $(this).html(clean_data);
        });
        $("#id_memory_mb option").each(function(){
            if(mem_value === $(this).val()){
                $("#id_memory_mb option").removeAttr("selected");
                $(this).attr("selected", true);
            }
        });
        check_all();
        get_price();
    });
}

// get hour price
function get_hour_price(){
    var billing_item = horizon.modals.billing_item;
    var float_ip = 0;
    var image_price = 0;
    if($("#launch_instance__selectimage").length >= 1 || $("#id_source_type").val() == 'image_id'){
        image_price = billing_item.image_1
    }
    var vcpus = parseInt($("#id_vcpus").val());
    var memory = parseInt($("#id_memory_mb").val());
    var hdd = parseInt($("#id_cloud_hdd").val())+parseInt($(".flavor_system_drive").text());
    if($("#id_is_create_floating_ip").attr("checked")){
        float_ip = 1
    }
    var instance_count = parseInt($("#id_count").val());
    var one_instance_price = (image_price+billing_item.instance_1+float_ip*billing_item.ip_1+
    vcpus*billing_item.cpu_1_core+(memory*billing_item.memory_1024_M)/1024+hdd*billing_item.disk_1_G);
    return (instance_count*one_instance_price).toFixed(4)
}

//init price field

function get_price() {
    var hour_price = get_hour_price();
    var month_price = horizon.modals.get_mon_price(hour_price);
    $(".price #price").text(hour_price);
    $(".small-price #mon_price").text(month_price);
}

//init price
function init_price() {
    $.get(get_real_url()+"/instances/api?billing_item=billing_item",function(data){
      	  var data_json = eval('(' + data + ')');
          horizon.modals.billing_item = data_json;
          get_price();
          display_unit_price();
    });
}

//display unit price

function display_unit_price() {
    if($("#launch_instance__selectimage .table.flavor_table").children().children().eq(0).find('td').length == 3)
    {return false;}
    var unit_price;
    unit_price = horizon.modals.billing_item;
    var price = [unit_price.image_1+'/时',unit_price.cpu_1_core+'/核/时',
        unit_price.memory_1024_M+'/G/时',unit_price.disk_1_G+'/G/时',unit_price.disk_1_G+'/G/时',unit_price.ip_1+'/个/时'];
    for(var i = 0;i < price.length;i++){
        $("#launch_instance__selectimage .table.flavor_table").children().children().eq(i).append('<td>¥'+price[i]+'</td>');
        $("#launch_instance__selectconfig .table.flavor_table").children().children().eq(i).append('<td>¥'+price[i]+'</td>');
        $("#launch_instance__baseinfo .table.flavor_table").children().children().eq(i).append('<td>¥'+price[i]+'</td>');
    }
}

//return image tooltip
function get_image_tooltip(image) {
    var image_name;
    if (image.length > 10){
        image_name = image.substr(0,10)+'...';
    }
    else{
        image_name = image;
    }
    $(".table.flavor_table .provider-filter").attr('data-original-title',image);
    $(".table.flavor_table .provider-filter").text(image_name);

}

// init quotas
function init_quotas() {
    $.get(get_real_url()+"/instances/api?avl=avl", function(data) {
        var data_json = eval('(' + data + ')');

        $('#id_cloud_hdd').attr('hdd_avl', data_json.hdd);
        $('#id_cloud_hdd').attr('vcpus_avl', data_json.vcpus);
        $('#id_cloud_hdd').attr('mem_avl', data_json.memory);
        $('#id_cloud_hdd').attr('hdd_count_avl', data_json.hdd_count);
        $('#id_cloud_hdd').attr('float_ip_avl', data_json.float_ip);
        $('#id_cloud_hdd').attr('instance_count_avl', data_json.count);

        g_is_init_quotas = true;
        check_all();
    });
}

// like main()
$(function(){
    init_quotas();

    init_select_public_image_option();
    init_image_filter();
    init_image_filter_for_public_custom();
    init_volume_and_snap_info();
    init_select_cpu_and_memory_option();
    init_flavor_table();
    init_floating_ip_input();
    init_data_volume_slider_and_input();
    init_instance_count_input();
    init_script_input();
    init_next_btn();
    init_final_btn();
});
