<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi"
	uri="http://fione.codelibs.org/functions"
%>
<div class="direct-chat-messages" style="height:auto;">
	<div class="direct-chat-msg right">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-right"><la:message key="labels.easyml_you" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-user fa-2x float-right" style="color:#64a1fc;"></em></span>
		<div class="direct-chat-text" style="background: #fff;"><la:message key="labels.easyml_what_do_you_think" /></div>
	</div>
	<div class="direct-chat-msg">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-left"><la:message key="labels.easyml_fione" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<c:choose>
				<c:when test="${predictionMetric.accuracy<=0.2}">
					<div><la:message key="labels.easyml_what_do_you_think_answer1" arg0="${fi:frameName(frameId)}" arg1="${f:h(responseColumn)}" arg2="${contextPath}/admin/automl/job/${f:u(projectId)}"/></div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.2 and predictionMetric.accuracy<=0.4}">
					<div><la:message key="labels.easyml_what_do_you_think_answer2" arg0="${fi:frameName(frameId)}" arg1="${contextPath}/admin/automl/job/${f:u(projectId)}" /></div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.4 and predictionMetric.accuracy<=0.6}">
					<div><la:message key="labels.easyml_what_do_you_think_answer3" /></div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.6 and predictionMetric.accuracy<=0.8}">
					<div><la:message key="labels.easyml_what_do_you_think_answer4" /></div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.8}">
					<div><la:message key="labels.easyml_what_do_you_think_answer5" /></div>
				</c:when>
			</c:choose>
		</div>
	</div>
	<c:if test="${predictionMetric.accuracy>0.4}">
	<div class="direct-chat-msg right">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-right"><la:message key="labels.easyml_you" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-user fa-2x float-right" style="color:#64a1fc;"></em></span>
		<div class="direct-chat-text" style="background: #fff;"><la:message key="labels.easyml_which_model_should_I_use" /></div>
	</div>
	<div class="direct-chat-msg">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-left"><la:message key="labels.easyml_fione" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<div><la:message key="labels.easyml_which_model_should_I_use_answer" arg0="${contextPath}/admin/automl/model/${f:u(projectId)}/${f:u(leaderboard.models[0].name)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" arg1="${f:h(leaderboard.models[0].name)}"/></div>
		</div>
	</div>
	<div class="direct-chat-msg right">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-right"><la:message key="labels.easyml_you" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-user fa-2x float-right" style="color:#64a1fc;"></em></span>
		<div class="direct-chat-text" style="background: #fff;"><la:message key="labels.easyml_how_do_i_get_result" /></div>
	</div>
	<div class="direct-chat-msg">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-left"><la:message key="labels.easyml_fione" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<div><la:message key="labels.easyml_how_do_i_get_result_answer" arg0="${contextPath}/admin/easyml/prediction/${f:u(projectId)}?did=${f:u(dataSetId)}&lid=${f:u(leaderboardId)}"/></div>
		</div>
	</div>
	<div class="direct-chat-msg right">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-right"><la:message key="labels.easyml_you" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-user fa-2x float-right" style="color:#64a1fc;"></em></span>
		<div class="direct-chat-text" style="background: #fff;"><la:message key="labels.easyml_how_do_i_integrate" /></div>
	</div>
	<div class="direct-chat-msg">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-left"><la:message key="labels.easyml_fione" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<div><la:message key="labels.easyml_how_do_i_integrate_answer" arg0="${contextPath}/admin/automl/serving/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&mid=${f:u(leaderboard.models[0].name)}"/></div>
		</div>
	</div>
	</c:if>
	<div class="direct-chat-msg">
		<div class="direct-chat-infos clearfix">
			<span class="direct-chat-name float-left"><la:message key="labels.easyml_fione" /></span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<div><la:message key="labels.easyml_any_comments" /></div>
		</div>
	</div>

</div>