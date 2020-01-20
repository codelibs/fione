<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi"
	uri="http://fione.codelibs.org/functions"
%>
<div class="direct-chat-messages" style="height:auto;">
	<div class="direct-chat-msg right">
		<div class="direct-chat-info clearfix">
			<span class="direct-chat-name pull-right">You</span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-user fa-2x pull-right" style="color:#64a1fc;"></em></span>
		<div class="direct-chat-text" style="background: #fff;">What do you think this result?</div>
	</div>
	<div class="direct-chat-msg">
		<div class="direct-chat-info clearfix">
			<span class="direct-chat-name pull-left">Fione</span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<c:choose>
				<c:when test="${predictionMetric.accuracy<=0.2}">
					<div>Prediction Accuracy is unsatisfactory... You cannot use generated models.</div>
					<div><strong>${fi:frameName(frameId)}</strong> may not contain important features to predict <strong>${f:h(responseColumn)}</strong>.</div>
					<div>To improve the accuracy, you need to check the current data and create a new dataset containing meaningful columns.</div>
					<div>I suggest you try it with other dataset again.</div>
					<div>Please click <a href="${contextPath}/admin/automl/details/${f:u(projectId)}">Project View</a> to check more details.</div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.2 and predictionMetric.accuracy<=0.4}">
					<div>Prediction Accuracy is low. You need to improve <strong>${fi:frameName(frameId)}</strong>.</div>
					<div>Adding input columns or data, the accuracy may increase.</div>
					<div>Please click <a href="${contextPath}/admin/automl/details/${f:u(projectId)}">Project View</a> to check more details.</div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.4 and predictionMetric.accuracy<=0.6}">
					<div>Prediction Accuracy is good.</div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.6 and predictionMetric.accuracy<=0.8}">
					<div>Prediction Accuracy is very good.</div>
				</c:when>
				<c:when test="${predictionMetric.accuracy>0.8}">
					<div>Prediction Accuracy is excellent!</div>
				</c:when>
			</c:choose>
		</div>
	</div>
	<c:if test="${predictionMetric.accuracy>0.4}">
	<div class="direct-chat-msg right">
		<div class="direct-chat-info clearfix">
			<span class="direct-chat-name pull-right">You</span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-user fa-2x pull-right" style="color:#64a1fc;"></em></span>
		<div class="direct-chat-text" style="background: #fff;">Which model should I use?</div>
	</div>
	<div class="direct-chat-msg">
		<div class="direct-chat-info clearfix">
			<span class="direct-chat-name pull-left">Fione</span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<div><a href="${contextPath}/admin/automl/model/${f:u(projectId)}/${f:u(leaderboard.models[0].name)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">${f:h(leaderboard.models[0].name)}</a> is a best model in generated ones.</div>
			<div>Please upload <a href="${contextPath}/admin/easyml/prediction/${f:u(projectId)}?did=${f:u(dataSetId)}&lid=${f:u(leaderboardId)}">DATA File</a> if you would like to append the prediction to it.</div>
		</div>
	</div>
	</c:if>
	<div class="direct-chat-msg">
		<div class="direct-chat-info clearfix">
			<span class="direct-chat-name pull-left">Fione</span>
		</div>
		<span class="direct-chat-img"><em class="fas fa-robot fa-2x" style="color: #f39c12;"></em></span>
		<div class="direct-chat-text">
			<div>If you have any questions/comments, please file it to <a href="https://github.com/codelibs/fione/issues" target="_blank">github.com/codelibs/fione</a>.</div>
		</div>
	</div>

</div>