function cdn (type, domain_id, start, end) {
    $.getJSON('json?' + 'type=' + type + '&' + 'domain_id=' + domain_id + '&' + 'start=' + start + '&' + 'end=' + end +'&'+'callback=?', function (data) {
                 var unit, danwei;
                 if (typeof data[0] == 'undefined' ){
                 		$('#chart').children().remove();
                        $('#chart').append('<div align="center">抱歉，此时间段无报表</div>');
                     return false;
                 }
                 var start = data[0][0];
                 var date_start = start.split(' ')[0];
                 var date_start_format = date_start.split('-');
                 var date_start_hms = start.split(' ')[1];
                 var date_start_hms_format = date_start_hms.split(':');
                 var to = data[data.length - 1][0];
                 var date_to = to.split(' ')[0];
                    var clean_data = [],init = 0;
                    for(var i=0;i<data.length;i++){
                            clean_data.push(data[i][1]);
                            init += data[i][1];
                        }
                    if (type != 'flow' && type != 'io') {
                        unit = '';
                        danwei = 'requests';
                        $("#message").remove();
                        $("#message_box").html(
                            "<button id='message' class='alert alert-warning'>" +
                            "该时间段总请求数:"+init+"</button>");
                    }
                    else if (type != 'requests' && type != 'flow'){
                        unit = 'Mb/s';
                        danwei = 'io(Mb/s)';
                        $("#message").remove();
                        $("#message_box").html(
                        "<button id='message' class='alert alert-warning'>" +
                        "该时间段带宽峰值:"+Math.max.apply(null,clean_data)+"Mb/s</button>");
                    }
                    else {
                        unit = 'MB';
                        danwei = 'traffic(MB)';
                        $("#message").remove();
                        $("#message_box").html(
                        "<button id='message' class='alert alert-warning'>" +
                        "该时间段总流量:"+(init/1024).toFixed(4)+"GB</button>");
                    }

                 $('#chart').highcharts({
                     credits: {
                         enabled: false
                     },
                     chart: {
                         zoomType: 'x'
                     },
                     title: {
                         text: date_start + '至' + date_to + '报表'
                     },
                     subtitle: {
                         text: document.ontouchstart === undefined ?
                                 '在绘图区域中单击并拖动缩放' :
                                 ''
                     },
                     xAxis: {
                         type: 'datetime'

                     },
                     yAxis: {
                         title: {
                             text:danwei
                         },
                         min: 0,
                         plotLines: [{
                             value: 0,
                             width: 1,
                             color: '#808080'
                                    }]
                     },
                      tooltip: {
                        valueSuffix: unit
                      },
                     legend: {
                         enabled: false
                     },
                     plotOptions: {
                         area: {
                             fillColor: {
                                 linearGradient: {
                                     x1: 0,
                                     y1: 0,
                                     x2: 0,
                                     y2: 1
                                 },
                                 stops: [
                                     [0, Highcharts.getOptions().colors[0]],
                                     [1, Highcharts.Color(Highcharts.getOptions().colors[0]).setOpacity(0).get('rgba')]
                                 ]
                             },
                             marker: {
                                 radius: 2
                             },
                             lineWidth: 1,
                             states: {
                                 hover: {
                                     lineWidth: 1
                                 }
                             },
                             threshold: null
                         }
                     },

                     series: [{
                         type: 'area',
                         name: danwei,
                         data: clean_data,
                         pointStart: Date.UTC(date_start_format[0],date_start_format[1]-1,date_start_format[2],
                                 date_start_hms_format[0], date_start_hms_format[1],date_start_hms_format[2]),
                         pointInterval: 300*1000
                     }]
                 });
             });
         };
        $(function(){
             var type = $('#monitor_type option:selected').val();
             var domain_id = $('#id_domain_id option:selected').val();
             var start = $('#id_start').val();
             var end = $('#id_end').val();
             cdn(type, domain_id, start, end);});

         $("#monitor_type").change(function(){
             var type = $('#monitor_type option:selected').val();
             var domain_id = $('#id_domain_id option:selected').val();
             var start = $('#id_start').val();
             var end = $('#id_end').val();
             cdn(type, domain_id, start, end)});

         $('#id_domain_id').change(function(){
             var type = $('#monitor_type option:selected').val();
             var domain_id = $('#id_domain_id option:selected').val();
             var start = $('#id_start').val();
             var end = $('#id_end').val();
             cdn(type, domain_id, start, end);
             if($('#admin_date_form').length >= 1){
                   $('#admin_date_form').submit();
             }
         });

         $('#submit').bind('click', function(){
             var type = $('#monitor_type option:selected').val();
             var domain_id = $('#id_domain_id option:selected').val();
             var start = $('#id_start').val();
             var end = $('#id_end').val();
             cdn(type, domain_id, start, end)});

/**
 * Created by gaga on 15-11-5.
 */
