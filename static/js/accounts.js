var ExchRate = 0;
var ExchMaxG = 0;


function stringToDate(s) {
  var dateParts = s.split(' ')[0].split('-'); 
  var timeParts = s.split(' ')[1].split(':');
  var d = new Date(dateParts[0], --dateParts[1], dateParts[2]);
  d.setHours(timeParts[0], timeParts[1], timeParts[2])

  return d
}

function stringToGMTDate(s) {
  var dateParts = s.split(' ')[0].split('-'); 
  var timeParts = s.split(' ')[1].split(':');
  var dateStr = `${dateParts[0]}-${("0"+dateParts[1]).substr(-2)}-${("0"+dateParts[2]).substr(-2)}T${timeParts[0]}:${timeParts[1]}:${timeParts[2]}.000Z`;
  var d = new Date(dateStr);
  return d;
}



function SwitchDisplayDataDiv(index){
	var list = ["ChngInfoDiv", "AccInfoDiv", "WebshopLogDiv"];
	
	list.forEach((x, idx) => {
		document.getElementById(x).style.display=idx == index ? 'block' : 'none';
	});

}
function SendNewData(){
	var d1 = document.getElementById('CurUnam').value+"-"+document.getElementById('CurUId').value+"-"+document.getElementById('OldUnam').value+"-"+document.getElementById('OldUId').value;
	var d2 = document.getElementById('CurPwd').value+"-"+document.getElementById('NewPwd1').value+"-"+document.getElementById('NewPwd2').value;
	var d3 = document.getElementById('Mail').value;
	var d4 = document.getElementById('RealName').value;
	var d5 = 0;
	var d6 = document.getElementById('dob-year').value+"-"+document.getElementById('dob-month').value+"-"+document.getElementById('dob-day').value;
	var d7 = document.getElementById('mstat').value;
	var g1 = document.getElementById('gender_female');
	var g2 = document.getElementById('gender_male');
	if (g1.checked){d5=2;}else if (g2.checked){d5=1;}
	SendDataWithAjax(13, [d1, d2, d3, d4, d5, d6, d7]);
}
function RequestUserData(n){
	var uid = n==1
		? document.getElementById('LoadUserId').value
		: (document.getElementById('CurUId').value || document.getElementById('LoadUserId').value);
	var lid = document.getElementById('OldUId').value;
	var dArr;
	if (n==1){
		SendDataWithAjax(1, [uid]);
	}else if (n==2){
		var am = parseInt(document.getElementById('AddGoldAmount').value,10)||0;
		if ((am > 0)&&(am < 10000000)){
			dArr=[uid, am];
		}else{
			alert('Please type a number between 1-99999.');
		}
	}else if (n==3){
		var am = parseInt(document.getElementById('AddPointAmount').value,10)||0;
		if ((am > 0)&&(am < 10000000)){
			dArr=[uid, am];
		}else{
			alert('Please type a number between 1-99999.');
		}
	}else if ((n==4)||(n==5)){
		//4 Add GM, 5 Del game rank
		dArr=[uid];
	}else if (n==8){
		dArr=[uid];	
	}else if (n==9){
		var am = parseInt(document.getElementById('OldDate').value,10)||0;
		if ((am > 0)&&(am < 36500)){
			dArr=[am];
		}else{
			alert('Please type a number between 1-36500.');
		}
	}else if ((n==10)||(n==11)){
		//10 gold, 11 point:  group reward adding
		var am  = parseInt(document.getElementById('OldDate1').value,10)||0;
		var am1 = parseInt(document.getElementById('rewAmount').value,10)||0;
		if ((am > -1)&&(am < 36500)&&(am1 > 0)&&(am1 < 9999999)){
			dArr=[am1, am];
		}else{
			alert('Please type a number.');
		}
	}
	if ((n>1)&&(n<12)&&(dArr.length>0)){
		SendDataWithAjax((n+1), dArr);
	}
}

var BanDialogTargetId = 0;

function OpenBanDialog(roleId, roleName){
	BanDialogTargetId = roleId;
	document.getElementById('BanDialogChar').textContent = roleName+' ['+roleId+']';
	document.getElementById('BanDlgType').selectedIndex = 0;
	document.getElementById('BanDlgDur').value = '3600';
	document.getElementById('BanDlgReason').value = 'Take a rest!';
	document.getElementById('BanDialog').style.display = 'flex';
}

function CloseBanDialog(){
	document.getElementById('BanDialog').style.display = 'none';
}

function ConfirmBanDialog(){
	var banType = document.getElementById('BanDlgType').value;
	var dur = parseInt(document.getElementById('BanDlgDur').value,10)||0;
	var reason = document.getElementById('BanDlgReason').value;
	if (dur < 5){
		alert('Duration must be at least 5 seconds.');
		return;
	}
	CloseBanDialog();
	SendBanRequest(BanDialogTargetId, banType, dur, reason);
}

function UnbanCharacter(roleId, banType){
	if (!confirm('Unban this character now?')) return;
	SendBanRequest(roleId, banType, 5, 'Unban');
}

function SendBanRequest(targetId, banType, duration, reason){
	var bannerId = 1024;
	var gmId = -1;
	SendDataWithAjax(7, [bannerId, targetId, banType, gmId, reason, duration]);
}

function ToggleGM(){
	var gmBtn = document.getElementById('GmToggleBtn');
	var isGm = gmBtn && gmBtn.getAttribute('data-isgm')=='1';
	RequestUserData(isGm ? 5 : 4);
}

function UpdateGmToggleBtn(urank){
	var gmBtn = document.getElementById('GmToggleBtn');
	if (!gmBtn) return;
	if (urank > 0){
		gmBtn.textContent = 'Rem. GM';
		gmBtn.className = 'px-2 py-1.5 bg-amber-700 hover:bg-amber-600 border border-amber-600 rounded text-xs text-white transition';
		gmBtn.setAttribute('data-isgm','1');
	}else{
		gmBtn.textContent = 'Add GM';
		gmBtn.className = 'px-2 py-1.5 bg-green-700 hover:bg-green-600 border border-green-600 rounded text-xs text-white transition';
		gmBtn.setAttribute('data-isgm','0');
	}
}

function UserSearch(){
	var txt = document.getElementById('SearchUser').value;
	var sType = 0;
	txt = txt.trim();
	
	if (txt==""){	
		sType = 1;
	}else if (isIPaddress(txt)){
		sType = 2;
	}else if (isNum (txt)){
		sType = 3;
	}else if (isAlphaNum (txt)){
		sType = 4;
	}else if (isEmiladdress (txt)){
		sType = 5;
	}else if (txt=="*"){
		sType = 6;
	}else if (isNegNum (txt)){
		txt = txt.substr(1)
		sType = 7;	
	}else if (txt=="@"){
		sType = 8;
	}else if (txt=="@*"){
		sType = 9;
	}

	if (sType > 0){
		var dArr=[txt,sType];
		SendDataWithAjax(2, dArr);
	}else{
		alert("You need write one from following data to input field: \n- username or real name (type name, example: shadow)\n- email adress (example: your@mail.com)\n- ip address (example: 79.84.75.89)\n- account id (type number)\n- who is online (type: *)\n- show Game Masters (type: @)\n- who was online in last x day (type negative number, example: -3)");
	}
}

function isIPaddress(ipaddress) {  
 if (/^(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$/.test(ipaddress)){  
    return true;  
  }  
	return false;  
}  

function isAlphaNum (str){
	var alphaNumRGX=/^[a-z\d]+$/i;
	return (alphaNumRGX.test(str) &&(str.length > 1));
}
function isEmiladdress (str){
	var emailRGX = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
	return emailRGX.test(str);
}

function isNum (str){
	return ((parseInt(str) == str) && (parseInt(str) > 0));
}	

function isNegNum (str){
	if (str.length > 1){
		return ((str.substr(0, 1) == "-") && (parseInt(str.substr(1)) > 0));
	}else{
		return false;
	}
}

function CheckExchCost(){
	setTimeout(function(){
		var ReqGoldInp = document.getElementById('ExchGAmount');
		var ReqGold = ReqGoldInp.value;
		var PCost;
		ReqGold = ReqGold.trim();
		if (ReqGold != parseInt(ReqGold)){
			ReqGold = 0;
		}
		ReqGold = parseInt(ReqGold, 10);
		if (ExchMaxG > 99999){ExchMaxG=99999;}
		if (ReqGold > ExchMaxG){ReqGold=ExchMaxG;}
		if (ReqGold < 0){ReqGold=0;}
		ReqGoldInp.value = parseInt(ReqGold, 10);
		PCost = ExchRate*ReqGold;
		PCost = parseInt(PCost, 10)||0;
		document.getElementById('ExchPCost').innerHTML = '<b>'+PCost+'</b>';		
	},300);
}

function ExchangePointToGold(){
	var ReqGold = parseInt(document.getElementById('ExchGAmount').value, 10)||0;
	if (ReqGold > 0){
		SendDataWithAjax(14, [ReqGold]);
	}
}

function EditUserData(userData){
	var userD=JSON.parse(userData);
	if (userD[0]["error"]!=""){
		alert(userD[0]["error"]);
	}else{
		SwitchDisplayDataDiv(1);
		if (Object.keys(userD[1].length>12)){
			var genderN=["","Male","Female"];
			var rankN=["Member","Game Master"];
			var aself=userD[1]["self"];
			var uid=userD[1]["id"];
			var uname=userD[1]["username"];
			var upass=userD[1]["password"];
			var urank=userD[1]["rank"];
			var usrank=userD[1]["srank"];
			var urn=userD[1]["truename"];
			var uem=userD[1]["email"];
			var uct=userD[1]["creatime"];
			var ubd=userD[1]["birthday"];
			var ugnd=userD[1]["gender"];
			var userRegIp=userD[1]["regIp"];
			var userLoginIp=userD[1]["loginIp"];
			var urn_ext=uname;
			if ((urank>0)||(usrank>0)){
				urn_ext=urn_ext+" ["+uid+"]";
			}
			document.getElementById('AccInfoBanRow').style.display='none';  
			document.getElementById('AccInfoZone').style.display='none';  
			document.getElementById('AccInfoAv').innerHTML='';
			document.getElementById('AccInfoNa').innerHTML=urn_ext;
			document.getElementById('AccInfoRN').innerHTML=urn;
			document.getElementById('AccInfoPw').innerHTML=upass;
			document.getElementById('AccInfoEm').innerHTML=uem;
			document.getElementById('AccInfoGe').innerHTML=genderN[ugnd];
			document.getElementById('AccInfobd').innerHTML=ubd;
			var raEl = document.getElementById('AccInfoRa');
			raEl.textContent = rankN[urank];
			raEl.style.color = urank > 0 ? '#f87171' : '#4ade80';
			document.getElementById('AccInfoRD').innerHTML=uct;
			document.getElementById('AccInfoRegIp').innerHTML=userRegIp;
			document.getElementById('AccInfoLoginIp').innerHTML=userLoginIp;
			document.getElementById('CurUnam').value=uname;
			document.getElementById('CurUId').value=uid;
			document.getElementById('OldUnam').value=uname;
			document.getElementById('OldUId').value=uid;
			document.getElementById('CurPwd').value=upass;
			document.getElementById('NewPwd1').value=upass;
			document.getElementById('NewPwd2').value=upass;
			document.getElementById('Mail').value=uem;
			document.getElementById('RealName').value=urn;
			var bdate=ubd.split(" ");
			bdate=bdate[0].split("-");
			var LYear=bdate[0]||0;
			var LMonth=bdate[1]||0;
			var LDay=bdate[2]||0;
			var cYear=parseInt(parent.document.getElementById('dob-year').options[2].value,10);
			document.getElementById('gender_male').checked=false;
			document.getElementById('gender_female').checked=false;
			if (ugnd==1){document.getElementById('gender_male').checked=true;}else if (ugnd==2){document.getElementById('gender_female').checked=true;}
			if (LYear>0){LYear=cYear-parseInt(LYear,10)+2;}
			if (LMonth>0){LMonth=parseInt(LMonth,10)+1;}
			if (LDay>0){LDay=parseInt(LDay,10)+1;}
			document.getElementById('dob-year').selectedIndex=LYear;
			document.getElementById('dob-month').selectedIndex=LMonth;
			document.getElementById('dob-day').selectedIndex=LDay;
			document.getElementById('mstat').selectedIndex = urank;
			UpdateGmToggleBtn(urank);
		}
		if (Object.keys(userD[2]).length>2){
			var lastlog=userD[2]["lastlogin"];
			var zoneid=userD[2]["zoneid"];
			var zonelid=userD[2]["zonelocalid"];
			document.getElementById('AccInfoLL').innerHTML=lastlog;
			if ((parseInt(zoneid, 10)||0)>0){
				document.getElementById('AccInfoZone').style.display="table-row";
				document.getElementById('AccInfoZId').innerHTML="map id: "+zoneid+" ["+zonelid+"]";
				document.getElementById('AccInfoStatus').innerHTML='<span style="color:#22c55e;font-weight:600;">&#x25CF; Online</span>';
			}else{
				document.getElementById('AccInfoZone').style.display="none";
				document.getElementById('AccInfoStatus').innerHTML='<span style="color:#ef4444;font-weight:600;">&#x25CF; Offline</span>';
			}
		}
		var table = document.getElementById('GoldLogTable');
		var row;
		var cell;
		var clogc=Object.keys(userD[3]).length;
		table.innerHTML = '';
		if (clogc>0){
			row = table.insertRow(-1);
			['Gold Amount','When','Status'].forEach(function(h, idx){
				var th = document.createElement('th');
				th.textContent = h;
				th.className = idx===2 ? 'text-center' : 'text-left';
				row.appendChild(th);
			});
			for (var i=0; i<clogc; i++){
				var entry = userD[3][i];
				var isPending = entry["pending"] == 1;
				row = table.insertRow(-1);
				cell = row.insertCell(0);
				cell.innerHTML='<b>'+(entry["cash"] / 100)+'</b>';
				cell = row.insertCell(1);
				cell.innerHTML=entry["fintime"];
				cell = row.insertCell(2);
				cell.className = 'text-center';
				if (isPending) {
					cell.innerHTML='<span class="text-amber-500 text-[10px] font-semibold">PENDING</span>';
				} else {
					cell.innerHTML='<span class="text-emerald-400 text-[10px] font-semibold">RECEIVED</span>';
				}
			}
		}else{
			row = table.insertRow(-1);
			cell = row.insertCell(0);
			cell.className = 'text-center text-slate-600 italic p-2';
			cell.colSpan = '3';
			cell.textContent='No transaction history.';
		}
		document.getElementById('CharList').innerHTML='<tr><td style="color:#64748b;font-style:italic;padding:6px 0;" colspan="3">Loading characters…</td></tr>';
		document.getElementById('AccInfoCI').innerHTML='…';
		(function(loadUid, loadSrank){
			var csrf=document.cookie.match(/csrf_token=([^;]+)/);
			csrf=csrf?csrf[1]:'';
			fetch('/api/accounts/chars',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':csrf},body:JSON.stringify({id:loadUid})})
			.then(function(r){return r.json();})
			.then(function(chars){RenderChars(chars,loadSrank);})
			.catch(function(){
				document.getElementById('CharList').innerHTML='<tr><td style="color:#ef4444;font-style:italic;" colspan="3">Failed to load characters.</td></tr>';
				document.getElementById('AccInfoCI').innerHTML='?';
			});
		})(uid, usrank);
CheckExchCost();
	}
}

function RenderChars(chars, usrank){
	var table = document.getElementById('CharList');
	if (!table) return;
	table.innerHTML = '';
	var charc = Object.keys(chars).length;
	document.getElementById('AccInfoCI').innerHTML = charc;
	if (charc > 0){
		var headers = usrank > 0 ? ['Name [ID]','Class (Lvl)','Coordinates','Ban Status','Actions'] : ['Name','Class (Lvl)'];
		var banTypeLabel = {1:'Account',2:'Chat (Acct)',3:'Chat',4:'Role'};
		var hrow = table.insertRow(-1);
		headers.forEach(function(h){
			var th = document.createElement('th'); th.textContent = h; th.className = 'text-left'; hrow.appendChild(th);
		});
		for (var i = 0; i < charc; i++){
			var role = chars[i];
			var row = table.insertRow(-1);
			var cell;
			if (usrank > 0){
				role.posX = ~~role.posX; role.posY = ~~role.posY; role.posZ = ~~role.posZ;
				if (role.map == 1){
					role.x = ~~(400 + role.posX / 10);
					role.y = ~~(role.posY / 10);
					role.z = ~~(550 + role.posZ / 10);
				}
				var roleData = JSON.stringify(role, null, 4);
				cell = row.insertCell(0);
				var anchor = document.createElement('a');
				anchor.href = '#';
				anchor.innerHTML = '<b>'+role.rolename+'</b> ['+role.roleid+']';
				anchor.onclick = (function(d){return function(){alert(d);};})(roleData);
				cell.appendChild(anchor);
				cell = row.insertCell(1);
				cell.innerHTML = role.rolepath+' '+role.roleclass+' ('+role.rolelevel+')';
				cell = row.insertCell(2);
				cell.innerHTML = 'x: '+role.posX+' y: '+role.posY+' z: '+role.posZ+' ['+role.map+']';

				var forbid = role.forbid || [];
				var isBanned = forbid.length > 0;
				cell = row.insertCell(3);
				if (isBanned){
					var f = forbid[0];
					var label = banTypeLabel[f.type] || ('Type '+f.type);
					var expText = '';
					if (f.time > 0 && f.createtime > 0){
						expText = 'until '+new Date((f.createtime+f.time)*1000).toLocaleString();
					}
					cell.innerHTML = '<span style="color:#f87171;font-weight:600;" title="'+(f.reason||'').replace(/"/g,'&quot;')+'">BANNED — '+label+'</span>'
						+ (expText ? '<br><span style="color:#64748b;font-size:10px;">'+expText+'</span>' : '');
				}else{
					cell.innerHTML = '<span style="color:#4ade80;">Clear</span>';
				}

				cell = row.insertCell(4);
				var actBtn = document.createElement('button');
				if (isBanned){
					actBtn.textContent = 'Unban';
					actBtn.className = 'px-2 py-0.5 bg-amber-700 hover:bg-amber-600 border border-amber-600 rounded text-xs text-white transition';
					actBtn.onclick = (function(rid, ftype){ return function(){ UnbanCharacter(rid, ftype); }; })(role.roleid, forbid[0].type);
				}else{
					actBtn.textContent = 'Ban';
					actBtn.className = 'px-2 py-0.5 bg-red-700 hover:bg-red-600 border border-red-600 rounded text-xs text-white transition';
					actBtn.onclick = (function(rid, rname){ return function(){ OpenBanDialog(rid, rname); }; })(role.roleid, role.rolename);
				}
				cell.appendChild(actBtn);
			} else {
				cell = row.insertCell(0);
				cell.innerHTML = '<b>'+role.rolename+'</b>';
				cell = row.insertCell(1);
				cell.innerHTML = role.rolepath+' '+role.roleclass+' ('+role.rolelevel+')';
			}
		}
	} else {
		var row = table.insertRow(-1);
		var cell = row.insertCell(0);
		cell.style.textAlign = 'center';
		cell.colSpan = '5';
		cell.innerHTML = '<i>... You have no character ...</i>';
	}
}

function EditUserList(userData){
	var userD=JSON.parse(userData);
	if (userD[0]["error"]!=""){
		alert(userD[0]["error"]);
	}else{
		var users = userD[1];
		var ipMap = {};
		var ipMap2 = {};
		var uc=Object.keys(users).length;
		var table = document.getElementById('UserTable');
		var row,cell,id,rn,un,rk,em;
		table.innerHTML = '';
		if (uc == 0){
			row = table.insertRow(-1);
			cell = row.insertCell(0);
			cell.style.cssText = 'padding:4px 8px;font-size:12px;color:#64748b;font-style:italic;';
			cell.textContent = 'Sorry but no result.';
		}else{
			for (var i=0;i<uc;i++){
				var user = users[i];

				if (!ipMap[user.ip]) { ipMap[user.ip] = []; }
				ipMap[user.ip].push(user.username);
				if (!ipMap2[user.loginIp]) { ipMap2[user.loginIp] = []; }
				ipMap2[user.loginIp].push(user.username);

				id=user["userid"];
				un=user["username"];
				rn=user["realname"];
				rk=user["rank"];
				em=user["email"];
				var zid=parseInt(user["zoneid"],10)||0;
				var dotColor = zid > 0 ? '#22c55e' : '#ef4444';
				var nameColor = rk > 0 ? '#f87171' : '#93c5fd';
				row = table.insertRow(-1);
				row.style.cssText = 'border-bottom:1px solid rgba(30,41,59,0.5);';
				cell = row.insertCell(0);
				cell.style.cssText = 'padding:4px 8px;';
				cell.innerHTML = "<a href='javascript:void(0);' title='ID: "+id+" — "+em+"'"
					+ " style='color:"+nameColor+";font-weight:500;'"
					+ " onClick='SendDataWithAjax(1,["+id+"]);document.getElementById(\"LoadUserId\").value="+id+";'>"+un+"</a>"
					+ " <span style='color:#475569;margin-left:4px;font-size:11px;'>["+id+"]</span>"
					+ " <span style='color:"+dotColor+";font-size:10px;margin-left:2px;'>&#x25CF;</span>";
			}
		}

		console.log(ipMap);
		console.log(ipMap2);
	}
}

function AdminToolHandler(userData, typ){
	var userD=JSON.parse(userData);
	if (userD[0]["error"]!=""){
		alert(userD[0]["error"]);
	}else{
		if (userD[0]["success"]!=""){
			alert(userD[0]["success"]);
		}
		var cId=parseInt(document.getElementById('CurUId').value,10)||0;
		if ((typ==11)||(typ==12)){
			SendDataWithAjax(1, [cId]);
		}else{
			if (userD[0]["reloaduserdata"]=="1"){
				SendDataWithAjax(1, [cId]);
			}
			if (userD[0]["reloaduserlist"]=="1"){
				UserSearch();
			}
		}
	}
}

function ChangeUserDataHandler(userData){
	var userD=JSON.parse(userData);
	var cId=parseInt(document.getElementById('CurUId').value,10)||0;
	if (userD[0]["error"]!=""){
		alert(userD[0]["error"]);
	}else{
		if (userD[0]["success"]!=""){
			alert(userD[0]["success"]);
		}
		if (userD[0]["reloaduserdata"]=="1"){
			SendDataWithAjax(1, [cId]);
		}
		if (userD[0]["reloaduserlist"]=="1"){
			UserSearch();
		}		
		
	}	
}



function SendDataWithAjax(typ, dArr) {
	var activexmodes=["Msxml2.XMLHTTP", "Microsoft.XMLHTTP"] //activeX versions to check for in IE
	if (window.ActiveXObject){ //Test for support for ActiveXObject in IE first (as XMLHttpRequest in IE7 is broken)
		for (var i=0; i<activexmodes.length; i++){
			try{
				xmlhttp = new ActiveXObject(activexmodes[i]);
			}catch(e){
			//suppress error
			}
		}
	}else if (window.XMLHttpRequest){
		// if Mozilla, Safari etc
		xmlhttp = new XMLHttpRequest();
	}else{
		return false;
	}
    xmlhttp.onreadystatechange = function() {
        if (this.readyState == 4 && this.status == 200) {
			var fdbck=JSON.parse(this.responseText);
		    if (typ==1){
				if (fdbck != ""){
					EditUserData(JSON.stringify(fdbck));
				}else{
					alert("Cannot load user data!");
				}
			}else if(typ==2){
				if (fdbck != ""){
					EditUserList(JSON.stringify(fdbck));
				}else{
					alert("Cannot load user list!");
				}
			}else if((typ>2)&&(typ<11)){
					AdminToolHandler(JSON.stringify(fdbck), typ);
			}else if((typ==11)||(typ==12)){
				if (fdbck != ""){
					AdminToolHandler(JSON.stringify(fdbck), typ);
				}else{
					alert("Cannot load user list!");
				}
			}else if(typ==13){
				if (fdbck != ""){
					ChangeUserDataHandler(JSON.stringify(fdbck));
				}else{
					alert("Cannot save data!");
				}
			}
        }
    };
	var obj;
	if (typ==1){
		xmlhttp.open("POST", "/api/accounts/load", false);
		obj = {"id":dArr[0]};
	}else if (typ==2){
		xmlhttp.open("POST", "/api/accounts/list", false);
		obj = {"sname":dArr[0], "stype":dArr[1]};
	}else if ((typ>2)&&(typ<13)){
		xmlhttp.open("POST", "/api/accounts/tool", false);
		if ((typ==3)||(typ==4)){
			obj = {"tool":(typ-1), "id":dArr[0], "amount":dArr[1]};	
		}else if ((typ==5)||(typ==6)||(typ==9)){
			obj = {"tool":(typ-1), "id":dArr[0]};
		}else if (typ==7){		
			obj = {"tool":(typ-1), "bannerid":dArr[0], "targetid":dArr[1], "bantype":dArr[2], "gmid":dArr[3], "banreason":dArr[4],"bandur":dArr[5]};
		}else if (typ==8){
			obj = {"tool":(typ-1), "bannerid":dArr[0], "targetid":dArr[1], "bantype":dArr[2], "gmid":dArr[3], "banreason":dArr[4],"bandur":"10"};
		}else if (typ==10){	
			obj = {"tool":(typ-1), "day":dArr[0]};
		}else if ((typ==11)||(typ==12)){	
			obj = {"tool":(typ-1), "amount":dArr[0], "day":dArr[1]};
		}
	}else if (typ==13){
		xmlhttp.open("POST", "/api/accounts/save", false);
		obj = {"NameStack":dArr[0], "PasswordStack":dArr[1], "Email":dArr[2], "RealName":dArr[3], "Gender":dArr[4], "DateYMD":dArr[5], "Rank":dArr[6]};
	}
	xmlhttp.setRequestHeader("Content-type", "application/json");	
	
	var myJSON = JSON.stringify(obj);
    xmlhttp.send(myJSON);
	return false;
}
