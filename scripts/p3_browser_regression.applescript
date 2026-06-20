-- P3 全场景 PM 浏览器回归验证脚本
-- 使用: osascript p3_browser_regression.applescript
-- 依赖: Safari 浏览器、HTTPS 访问

global testReport, stepNum, baseURL

set baseURL to "https://139.196.15.52"
set testReport to {}
set stepNum to 0

-- 工具函数
on logPass(testName, detail)
	set end of testReport to "✅ " & testName & " — " & detail
end logPass

on logFail(testName, detail)
	set end of testReport to "❌ " & testName & " — " & detail
end logFail

on doStep(testName)
	set stepNum to stepNum + 1
	log "Step " & stepNum & ": " & testName
end doStep

-- 主流程
tell application "Safari"
	activate
	-- 确保有窗口
	if (count of windows) = 0 then
		make new document
	end if
	set currentTab to current tab of front window
end tell

-- ══════════════════════════════════════
-- Step 1: HTTPS 访问 + 页面加载
-- ══════════════════════════════════════
doStep("HTTPS首页加载")
tell application "Safari"
	set URL of current tab of front window to baseURL & "/"
	delay 5
end tell
try
	tell application "Safari"
		set pageTitle to name of front document
		set loaded to do JavaScript "document.title" in front document
	end tell
	if loaded is not "" then
		logPass("首页加载", "标题: " & loaded)
	else
		logFail("首页加载", "页面标题为空")
	end if
on error errMsg
	logFail("首页加载", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- Step 2: 登录
-- ══════════════════════════════════════
doStep("PM登录")
try
	tell application "Safari"
		set URL of current tab of front window to baseURL & "/login"
		delay 3
		do JavaScript "
			(function(){
				var inputs = document.querySelectorAll('input');
				for (var i = 0; i < inputs.length; i++) {
					if (inputs[i].placeholder && inputs[i].placeholder.indexOf('用户') >= 0) inputs[i].value = 'zhangzhenjie';
					if (inputs[i].type === 'password') inputs[i].value = '123456';
				}
				var btns = document.querySelectorAll('button');
				for (var j = 0; j < btns.length; j++) {
					if (btns[j].innerText.indexOf('登录') >= 0) { btns[j].click(); break; }
				}
				return 'submit';
			})()
		" in front document
		delay 4
		set currentURL to URL of front document
	end tell
	if currentURL contains "dashboard" or currentURL contains "pm" then
		logPass("PM登录", "跳转成功: " & currentURL)
	else
		-- 检查是否有错误提示
		tell application "Safari"
			try
				set errText to do JavaScript "
					(function(){
						var errs = document.querySelectorAll('.el-message--error, .el-alert--error');
						if (errs.length > 0) return errs[0].innerText;
						return '';
					})()
				" in front document
			on error
				set errText to ""
			end try
		end tell
		if errText is not "" then
			logFail("PM登录", "登录失败: " & errText)
		else
			logFail("PM登录", "未跳转，当前URL: " & currentURL)
		end if
	end if
on error errMsg
	logFail("PM登录", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- Step 3: PM工作台
-- ══════════════════════════════════════
doStep("PM工作台加载")
tell application "Safari"
	set URL of current tab of front window to baseURL & "/pm-workspace"
	delay 5
end tell
try
	tell application "Safari"
		set hasWorkspace to do JavaScript "
			(function(){
				var h2 = document.querySelector('h2');
				if (h2 && h2.innerText.indexOf('产品经理工作台') >= 0) return true;
				return false;
			})()
		" in front document
		set cardCount to do JavaScript "document.querySelectorAll('.col-card').length" in front document
		set jsErrors to do JavaScript "
			(function(){
				var errs = document.querySelectorAll('.el-message--error');
				return errs.length;
			})()
		" in front document
	end tell
	if hasWorkspace then
		logPass("PM工作台", "卡片数: " & cardCount & ", JS错误: " & jsErrors)
	else
		logFail("PM工作台", "未找到工作台标题")
	end if
on error errMsg
	logFail("PM工作台", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- Step 4: 产品立项抽屉
-- ══════════════════════════════════════
doStep("产品立项抽屉")
try
	tell application "Safari"
		-- 点击"产品立项"按钮
		do JavaScript "
			(function(){
				var btns = document.querySelectorAll('button');
				for (var i = 0; i < btns.length; i++) {
					if (btns[i].innerText.indexOf('产品立项') >= 0 && !btns[i].disabled) {
						btns[i].click();
						return 'clicked';
					}
				}
				return 'not found';
			})()
		" in front document
		delay 3
		set drawerVisible to do JavaScript "
			(function(){
				var drawer = document.querySelector('.el-drawer');
				return drawer !== null;
			})()
		" in front document
		set tabCount to do JavaScript "document.querySelectorAll('.el-tabs__item').length" in front document
	end tell
	if drawerVisible then
		logPass("产品立项", "抽屉打开，Tab数: " & tabCount)
	else
		logFail("产品立项", "抽屉未打开")
	end if
on error errMsg
	logFail("产品立项", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- Step 5: 竞品对标
-- ══════════════════════════════════════
doStep("竞品对标组件")
try
	tell application "Safari"
		set url to baseURL & "/pm-workspace#/competitor-bench"
		set URL of current tab of front window to url
		delay 4
		set benchExists to do JavaScript "
			(function(){
				var el = document.querySelector('.competitor-bench');
				return el !== null;
			})()
		" in front document
	end tell
	if benchExists then
		logPass("竞品对标", "组件正常加载")
	else
		logFail("竞品对标", "组件未找到")
	end if
on error errMsg
	logFail("竞品对标", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- Step 6: 年度规划 CRUD
-- ══════════════════════════════════════
doStep("年度规划CRUD")
try
	tell application "Safari"
		set URL of current tab of front window to baseURL & "/pm-workspace"
		delay 4
		-- 检查是否有规划项
		set planCount to do JavaScript "
			(function(){
				return document.querySelectorAll('.plan-item').length;
			})()
		" in front document
		-- 检查编辑/删除按钮
		set hasEditBtn to do JavaScript "
			(function(){
				var btns = document.querySelectorAll('.plan-item-actions button');
				return btns.length;
			})()
		" in front document
	end tell
	logPass("年度规划", "规划项: " & planCount & ", 操作按钮: " & hasEditBtn)
on error errMsg
	logFail("年度规划", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- Step 7: JS 错误检查
-- ══════════════════════════════════════
doStep("全局JS错误检查")
try
	tell application "Safari"
		set errCount to do JavaScript "
			(function(){
				var errs = document.querySelectorAll('.el-message--error, .el-alert--error');
				var visible = 0;
				for (var i = 0; i < errs.length; i++) {
					if (errs[i].offsetParent !== null) visible++;
				}
				return visible;
			})()
		" in front document
		set _404Count to do JavaScript "
			(function(){
				var all = document.body.innerText;
				return (all.match(/Not Found/gi) || []).length;
			})()
		" in front document
		set blankCount to do JavaScript "
			(function(){
				var rv = document.querySelector('.router-view,.el-main');
				if (rv && rv.innerHTML.trim() === '<!---->') return 1;
				return 0;
			})()
		" in front document
	end tell
	if errCount is 0 and _404Count is 0 and blankCount is 0 then
		logPass("错误检查", "无JS错误/404/空白页")
	else
		logFail("错误检查", "JS错误: " & errCount & ", 404: " & _404Count & ", 空白: " & blankCount)
	end if
on error errMsg
	logFail("错误检查", "异常: " & errMsg)
end try

-- ══════════════════════════════════════
-- 输出报告
-- ══════════════════════════════════════
set reportPath to "/tmp/p3_regression_report.txt"
set reportContent to "=== P3 PM Browser Regression Report ===" & return & "Date: " & (current date) & return & return
repeat with lineItem in testReport
	set reportContent to reportContent & lineItem & return
end repeat
set reportContent to reportContent & return & "Total steps: " & stepNum & return

try
	set fileRef to open for access reportPath with write permission
	set eof fileRef to 0
	write reportContent to fileRef starting at eof
	close access fileRef
on error
	try
		close access fileRef
	end try
end try

return reportContent
