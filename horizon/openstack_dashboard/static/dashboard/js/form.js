var real_url=get_url()var icon="<i class='fa fa-times-circle font-size14'></i>";var fromError = {'inputUsername':{'empty':'用户名不能为空哦~','nolen':'用户名长度为 4-20 位','nopoint':'用户名禁用 . 符号','notype':'用户名格式错误','exsit':'用户名已注册'},'inputEmail':{'empty':'邮箱不能为空哦~','notype':'邮箱格式错误','exsit':'邮箱已注册'},'password':{'empty':'密码不能为空哦~','nolen':'密码长度为 6-20 位','noblank':'密码禁用空格','notype':'密码格式错误哦~'},'repassword':{'empty':'确认密码不能为空','nosame':'两次输入的密码不同'},'mobile':{'empty':'手机不能为空','notype':'手机格式错误','exsit':'手机已注册'},'mobile_yzm':{'empty':'手机验证码不能为空','nosame':'手机验证码错误'},'compName':{'empty':'公司名不能为空','exsit':'公司名已注册'},'industry':{'empty':'行业不能为空'},'agreenment':{'empty':'请接受Syscloud协议！'}};var page='register'; //区分页面var name_check='error';var email_check='error';var mobile_check='error';var mobileCode_check='error';var picCode_check='error';var company_check='error';//域名判断：  logoname=$("#logoTag").val();  if(logoname!=''){		$(".logo_horizontal").attr("src",'/images/'+logoname+'_front.png');		$("link[rel='shortcut icon']").attr("href",'/images/'+logoname+'.ico');		}else{ 	    $(".logo_horizontal").attr("src",'/static/dashboard/img/login_horizontal.png');    }$(document).ready(function(){		//设置高度：	height=window.screen.height;	$(".user_form .page_left").height(height);//登录页面链接调整$(".register.seturl").attr('href',real_url+'register/');$(".getpassword.seturl").attr('href',real_url+'getpassword/');$("#codeurl").attr('src',real_url+'register/');imgurl='<img src="'+real_url+'member/createCode/?id=" onClick="this.src=this.src+'+"1"+'" >'$(".user_form #checkCode").html(imgurl)//******************登录验证*********************    $("#btn-login").click(function(){       $("#form-error").hide();       $(".alert-danger").hide();       username=$("#id_username").val();       password=$("#id_password").val();       if(username==""){           $("#id_username").focus();           $("#form-error .text-danger").html(icon+'请输入账户名');           $("#form-error").show();           return false;       }else{		      if(checkPhone(username)){				  	$("#auth_type").val('telephone');				  }else if(checkEmail(username)){				 	$("#auth_type").val('email');		         }		   }       if(password==""){           $("#id_password").focus();           $("#form-error .text-danger").html(icon+'请输入密码');;           $("#form-error").show();           return false;       }	   	   //验证码验证：	     var inputCode = document.getElementById("yzm").value;		  inputCode=inputCode.toLocaleLowerCase();		  if (inputCode.length <= 0) {			 ErrorInput("yzm",'请输入验证码！');			 $("#yzm").focus();			 $("#form-error .text-danger").html(icon+'请输入验证码');			 $("#form-error").show();			 return false;		  }else{			   $.get(real_url+"member/checkCode/?code="+inputCode,function(data){				   data=eval("("+data+")")				   if(data.status!='OK'){						 error=data.error						 $("#checkCode img").click();						 $("#yzm").focus();						 $("#form-error .text-danger").html(icon+error);						 $("#form-error").show();						 return false;					}else{						$("#form_id_login").submit();						}			  })			  return false;          }         });       $("#id_username").blur(function(){	 	   var val=$("#id_username").val();	 		 var param='inputUsername='+val		     if(val==''){					 return false;   		      }		       if(checkPhone(val)){				  	$("#auth_type").val('telephone');				  }else if(checkEmail(val)){				 	$("#auth_type").val('email');		         }	  	});       //监控倒计时  $(".user_form .i-countdown,#send-voiceMessge").click(function() {	   var type="message";		   var inputCode = $("#yzm").val();	   inputCode=inputCode.toLocaleLowerCase();	  if($(".user_form .i-countdown").attr("disabled") || $("#send-voiceMessge").attr("disabled") ){		  alert("一次只能发送一种短信");		  return false;		  }      if($(this).attr('disabled'))         return false;          var mobile = $('#mobile').val();		 if(mobile=='')		 {			ErrorInput("mobile",fromError['mobile']['empty']);            return false;		 }else if (!checkPhone(mobile)) {			ErrorInput("mobile",fromError['mobile']['notype']);            return false;        }else if(mobile_check=="error"){			return false; 		}else{			 if(page=='register'){				 				  if (inputCode.length <= 0) {						 ErrorInput('yzm','请输入验证码');						 $("#yzmError").parent().parent().parent().addClass('has-error')							 return false;				  }				  if(picCode_check=="error")					    return false; 	 			  }				  if($(this).attr("id")=="send-voiceMessge"){		        type="voice";	          } 						  			sendmessage(mobile,type,inputCode)			countdown($(this), 60);	 					}     });}) //判断输入内容,包含多少字符 function AnalyzePasswordSecurityLevel(password,len) {    var securityLevelFlag = 0;    if(password==""){       return 0;    }    else if (password.length < len) {        return 0;    }    else {        if (/[a-z]/.test(password)){            securityLevelFlag++;    //lowercase        }        if (/[A-Z]/.test(password)){            securityLevelFlag++;    //uppercase        }         if(/[0-9]/.test(password)){            securityLevelFlag++;    //digital        }        if(containSpecialChar(password)){            securityLevelFlag++;    //specialcase        }        return securityLevelFlag;    }  }  function containSpecialChar(str)      {         var containSpecial = RegExp(/[(\ )(\~)(\!)(\@)(\#)(\$)(\%)(\^)(\&)(\*)(\()(\))(\-)(\_)(\+)(\=)(\[)(\])(\{)(\})(\|)(\\)(\;)(\:)(\')(\")(\,)(\.)(\/)(\<)(\>)(\?)(\)]+/);      return (containSpecial.test(str));      }      //倒计时公用函数function countdown(o, wait) {    if (wait == 0) {        o.attr("disabled", false);        o.text("重发验证码");		$("#send-voiceMessge").show();        wait = 60;    } else {        o.attr("disabled", true);        o.text("重新发送(" + wait + ")");        wait--;        setTimeout(function () {                countdown(o, wait);            },            1000);    }}//检查用户名。手机。邮箱是否 －－注册过$(function () {  $('[data-toggle="popover"]').popover();      $('#password').blur(function(){	  password=$.trim($('#password').val())	  if(password==''){			  ErrorInput("password",fromError['password']['empty']);		  }else if(!checkPwd(password)){			  ErrorInput("password",fromError['password']['notype']);			  }		  else{			  ErrorDel('password');			  }     });       $('#repassword').blur(function(){	  password=$.trim($('#password').val())	  repassword=$.trim($('#repassword').val())	  if(repassword==''){			        ErrorInput("repassword",fromError['repassword']['empty']);			   if(password==''){				    return false;				     ErrorInput("password",fromError['password']['empty']);				   }	 		  }else if(repassword!=password)		  	   ErrorInput("repassword",fromError['repassword']['nosame']);		  else{			   ErrorDel('repassword');			  }     });         $("#mobile_yzm").blur(function(){	   mobile_yzm=$.trim($("#mobile_yzm").val());	   if(mobile_yzm==''){			  ErrorInput("mobile_yzm",'验证码不能为空');			   }else{				    //ajax 调用手机验证码				   $.get(real_url+"member/checkMsg/?msg="+mobile_yzm+"&inputsafeToken="+safeToken,function(data){					   data=eval("("+data+")")					   if(data.status!='OK'){						   ErrorInput("mobile_yzm",data.error);						   return false;						   }else{			                ErrorDel('mobile_yzm');			               } 					})		                 }	});	   	$("#compName").blur(function(){	   compName=$.trim($("#compName").val());	   if(compName==''){			   ErrorInput("compName",fromError['compName']['empty']);			   }else{				     param="compName="+compName;		  			 items='compName';					 checkuser(param,items);		   		} 	});		$('#industry').on("change blur",function(){ 	   industry=$.trim($("#industry  option:selected").val());	   if(industry==''){			   ErrorInput("industry",fromError['industry']['empty']);			   }else{			   ErrorDel('industry');			  } 	});		$("#agreenment").click(function(){	   	if(!$(this).is(':checked')){			ErrorInput("agreenment",fromError['agreenment']['empty']);		}else{			ErrorDel('agreenment');			}    });	     $('#inputUsername,#inputEmail,.user_form .mobile').blur(function(){	  var val=$.trim($(this).val());	  var id=$(this).attr('id');	  var param='';	  var items=""	  if(val=='' && id!=''){		      ErrorInput(id,fromError[id]['empty']);	   }	  if($(this).hasClass('inputUsername')){		   if(inputUsername.length<4 || inputUsername.length>20){			   ErrorInput("inputUsername",fromError['inputUsername']['nolen']);			   return false;			   }else if(!checkName(val)){				   ErrorInput("inputUsername",fromError['inputUsername']['notype']);			       return false;				   }		   param="inputUsername="+val;		   items='inputUsername';	   }else if($(this).hasClass('inputEmail')){		   if(!checkEmail(val)){			   ErrorInput("inputEmail",fromError['inputEmail']['notype']);			   return false;			   }		   param="inputEmail="+val;		   items='inputEmail';	   }else if($(this).hasClass('mobile')){		   		   if(!checkPhone(val)){			   ErrorInput("mobile",fromError['mobile']['notype']);			   return false;			}		   param="mobile="+val;		   items='mobile';		   } 	  checkuser(param,items);  })    //验证码验证    $("#yzm").blur(function(){	   //验证码验证：			  var inputCode = $("#yzm").val();			  inputCode=inputCode.toLocaleLowerCase();			  if (inputCode.length <= 0) {				 ErrorInput('yzm','请输入验证码');				 $("#yzmError").parent().parent().parent().addClass('has-error')					 return false;			  }else{				  picCode_check="checking";				  ErrorInput("yzm","数据验证中...");				   $.get(real_url+"member/checkCode/?code="+inputCode,function(data){					   data=eval("("+data+")")					   if(data.status!='OK'){							 error=data.error							 $("#checkCode img").click();							 ErrorInput('yzm',error);							 $("#yzmError").parent().parent().parent().addClass('has-error')							}else{						   ErrorDel('yzm')						   $("#yzmError").parent().parent().parent().removeClass('has-error')						}				  })	  			    }		});  //表单提交	$("#btn-submit").click(function(){	  	var inputUsername=$.trim($("#inputUsername").val());		var inputEmail=$.trim($("#inputEmail").val());		var mobile=$.trim($("#mobile").val());		var password=$.trim($("#password").val());		var repassword=$.trim($("#repassword").val());		var mobile_yzm=$.trim($("#mobile_yzm").val());		var compName=$.trim($("#compName").val());		var industry=$.trim($("#industry  option:selected").val());		var hasError=0;	    if(inputUsername==''){			   ErrorInput("inputUsername",fromError['inputUsername']['empty']);			   hasError=1;		}else if(!checkName(inputUsername)){			   ErrorInput("inputUsername",fromError['inputUsername']['notype']);			   hasError=1;		}else if(name_check=="error"){			   hasError=1;		}   		if(inputEmail==''){			   ErrorInput("inputEmail",fromError['inputEmail']['empty']);			   hasError=1;			   }else if(!checkEmail(inputEmail)){			    ErrorInput("inputEmail",fromError['inputEmail']['notype']);			    hasError=1;			   }else if(email_check=="error"){				   hasError=1;			   }   		if(password==''){			   ErrorInput("password",fromError['password']['empty']);			   hasError=1;			   }else if(password.length<6 || password.length>20){			    ErrorInput("password",fromError['password']['nolen']);				hasError=1;			  }			if(repassword==''){			   ErrorInput("repassword",fromError['repassword']['empty']);			   hasError=1;			   }  	    if(mobile==''){			   ErrorInput("mobile",fromError['mobile']['empty']);			   hasError=1;		  }else if(!checkPhone(mobile)){			   ErrorInput("mobile",fromError['mobile']['notype']);			   hasError=1;		  }else if(mobile_check=="error"){				   hasError=1;				   }				   		 if(mobile_yzm==''){			   ErrorInput("mobile_yzm",fromError['mobile_yzm']['empty']);			   hasError=1;	     }else if(mobileCode_check=="error"){				hasError=1;	     }	    if(compName==''){				   ErrorInput("compName",fromError['compName']['empty']);			   	   hasError=1;			   }else if(company_check=="error"){				   hasError=1;				   }		if(industry==''){			   ErrorInput("industry",fromError['industry']['empty']);			   hasError=1;			   }	   		var inputCode = $("#yzm").val();	    inputCode=inputCode.toLocaleLowerCase();	    if (inputCode.length <= 0) {				 ErrorInput('yzm','请输入验证码');				 $("#yzmError").parent().parent().parent().addClass('has-error')					 hasError=1;		 }else if(picCode_check=="error"){				  hasError=1;          }	   if(!$("input[type='checkbox']").is(':checked')){			ErrorInput("agreenment",fromError['agreenment']['empty']);			hasError=1;		 }	     if(hasError==1)				return false; 				 		})		})//show errorfunction ErrorInput(id,error){	if(id=="yzm") picCode_check="error";	else if(id=="inputUsername") name_check='error';	else if(id=="inputEmail") email_check='error';	else if(id=="mobile") mobile_check='error';	else if(id=="mobile_yzm") mobileCode_check='error';	else if(id=="compName") company_check='error';	id_error="#"+id+"Error";	obj=$(id_error);	obj.html(icon+error);	obj.parent().parent().addClass('has-error');	obj.show(); 	}//del errorfunction ErrorDel(id){	if(id=="yzm") picCode_check="ok";	else if(id=="inputUsername") name_check='ok';	else if(id=="inputEmail") email_check='ok';	else if(id=="mobile") mobile_check='ok';	else if(id=="mobile_yzm") mobileCode_check='ok';	else if(id=="compName") company_check='ok';	obj=$("#"+id+"Error")	obj.html('');	obj.parent().parent().removeClass('has-error')	obj.hide(); 	}	function checkuser(param,items){		     if(param!=''){			 param+="&inputsafeToken="+safeToken;			 if(items=="mobile"){				  mobile_check="checking";				  ErrorInput(items,"数据验证中...");				 }			  $.get(real_url+"member/checkUser/?"+param,function(data){ 			 			  if(items=='mobile') 			  {				  mobile_yzm=$("#mobile_yzm").val();				  if(mobile_yzm!=''){					    $("#mobile_yzm").trigger("blur");					  }							  }               if(data=='Exist'){					   ErrorInput(items,fromError[items]['exsit']);				   }else if(data=='limitVisit'){					   ErrorInput(items,'非法的访问');					   return true;					   }					   else if(data=='safeTokenTimeout'){					   ErrorInput(items,'安全验证失效,请重新刷新注册页');					   return true;					   }else if(data=='safeTokenError'){					   ErrorInput(items,'安全验证失败,请重新刷新注册页');					   return true;					   }				   else{					   if(items=='compName'){						   checkproject(param,items)						   }else{							   	ErrorDel(items);					            return false;						    }					   }					   									             })		}	}		//项目名判断	function checkproject(param,items){	     if(param!='' && items=='compName'){			 param+="&inputsafeToken="+safeToken			  $.get(real_url+"member/checkproject/?"+param,function(data){               if(data=='Exist'){					   ErrorInput(items,fromError[items]['exsit']);				   }else if(data=='limitVisit'){					   ErrorInput(items,'非法的访问');					   }					   else if(data=='safeTokenTimeout'){					   ErrorInput(items,'安全验证失效,请重新刷新注册页面');					   }else if(data=='safeTokenError'){					   ErrorInput(items,'安全验证失败,请重新刷新注册页面');					   }				   else{					   ErrorDel(items);					   }          })		}	}		  function checkUserName(name){	name=$.trim(name)	if(name=="")		return false; 	var jc_yin = /[a-zA-Z]/g;	yin_str=name.match(jc_yin)	var count_yin=0	if(typeof(yin_str) != "undefined" &&  yin_str!=null){		 count_yin=yin_str.length;		 }    if(name.length<4 || name.length>20)		 $(".name-checklist #checklist_len").addClass("error");	else 		 $(".name-checklist #checklist_len").removeClass("error")	if(count_yin==0)		$(".name-checklist #checklist_acha").addClass("error")	else	 		$(".name-checklist #checklist_acha").removeClass("error")	 		 	if(!checkName(name))		 $(".name-checklist #checklist_cha").addClass("error")	else 		 $(".name-checklist #checklist_cha").removeClass("error")	}			//验证密码安全等级  function checkPassword(pwd){	if(pwd=="")		return false;    var objLow=document.getElementById("pwdLow");    var objMed=document.getElementById("pwdMed");    var objHi=document.getElementById("pwdHi");    objLow.className="pwd-strength-box";    objMed.className="pwd-strength-box";    objHi.className="pwd-strength-box";    if(pwd.indexOf(" ")> -1){		 $(".pwd-checklist #checklist_spa").addClass("error");		}else{			 $(".pwd-checklist #checklist_spa").removeClass("error");			}    if(pwd.length<6 || pwd.length>20)		 $(".pwd-checklist #checklist_len").addClass("error")	else 		 $(".pwd-checklist #checklist_len").removeClass("error")	if(!checkPwd(pwd))		 $(".pwd-checklist #checklist_cha").addClass("error")	else 		 $(".pwd-checklist #checklist_cha").removeClass("error")	    if(pwd.length<6){   		 objLow.className="pwd-strength-box-low";    }else{		var p1= (pwd.search(/[a-zA-Z]/)!=-1) ? 1 : 0;		var p2= (pwd.search(/[0-9]/)!=-1) ? 1 : 0;		var p3= (pwd.search(/[^A-Za-z0-9_]/)!=-1) ? 1 : 0;		var pa=p1+p2+p3;		if(pa==1){		objLow.className="pwd-strength-box-low";		}else if(pa==2){		objMed.className=objLow.className="pwd-strength-box-med";		}else if(pa==3){		objHi.className=objMed.className=objLow.className="pwd-strength-box-hi";		}    } }