<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %>
<form method="post" action="${contextPath}/admin/automl/">
<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
<input type="hidden" name="projectId" value="${f:h(project.id)}">
<div class="btn-group" role="toolbar" aria-label="Toolbar">
	<div class="btn-group" role="group">
		<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			<i class="fas fa-table"></i>
			<la:message key="labels.automl_menu_dataset" />
		</button>
		<ul class="dropdown-menu">
			<li><la:link href="/admin/automl/newdataset/${f:u(project.id)}" styleClass="btn btn-link btn-sm">
				<la:message key="labels.automl_upload_dataset" />
			</la:link></li>
		</ul>
	</div>
	<c:if test="${not empty frameId}">
	<div class="btn-group" role="group">
		<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			<i class="fas fa-columns"></i>
			<la:message key="labels.automl_menu_frame" />
		</button>
		<ul class="dropdown-menu">
			<li><la:link href="/admin/automl/columnlist/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				<la:message key="labels.automl_columnview" />
			</la:link></li>
			<li><la:link href="/admin/automl/dataview/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				<la:message key="labels.automl_dataview" />
			</la:link></li>
			<c:forEach var="module" items="${frameModules}">
			<li><la:link href="/admin/automl/module/${f:u(project.id)}/${f:u(module.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				${f:h(module.name)}
			</la:link></li>
			</c:forEach>
		</ul>
	</div>
	</c:if>
	<c:if test="${not empty frameId}">
	<div class="btn-group" role="group">
		<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			<i class="fas fa-hammer"></i>
			<la:message key="labels.automl_menu_machine_learning" />
		</button>
		<ul class="dropdown-menu">
			<li><la:link href="/admin/automl/setupml/${f:u(project.id)}/${f:u(frameId)}" styleClass="btn btn-link btn-sm">
				<la:message key="labels.automl_run_automl" />
			</la:link></li>
			<c:if test="${leaderboard != null}">
			<li><la:link href="/admin/automl/modellist/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				<la:message key="labels.automl_modelview" />
			</la:link></li>
			</c:if>
			<c:forEach var="module" items="${trainModules}">
			<li><la:link href="/admin/automl/module/${f:u(project.id)}/${f:u(module.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				${f:h(module.name)}
			</la:link></li>
			</c:forEach>
		</ul>
	</div>
	</c:if>
	<c:if test="${not empty frameId and leaderboard != null}">
	<div class="btn-group" role="group">
		<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			<i class="fas fa-file-signature"></i>
			<la:message key="labels.automl_predict" />
		</button>
		<ul class="dropdown-menu">
			<li><la:link href="/admin/automl/prediction/${f:u(project.id)}/${f:u(frameId)}/${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				<la:message key="labels.automl_predict_dataset" />
			</la:link></li>
			<c:forEach var="module" items="${predictModules}">
			<li><la:link href="/admin/automl/module/${f:u(project.id)}/${f:u(module.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-link btn-sm">
				${f:h(module.name)}
			</la:link></li>
			</c:forEach>
		</ul>
	</div>
	</c:if>
	<la:link href="/admin/automl/job/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-default">
		<i class="fas fa-tasks"></i>
		<la:message key="labels.automl_job" />
	</la:link>
</div>

<div class="float-right">
	<div class="btn-group" role="group">
		<button type="button" class="btn btn-default dropdown-toggle" data-toggle="dropdown" aria-haspopup="true" aria-expanded="false">
			<la:message key="labels.automl_options" />
			</button>
		<ul class="dropdown-menu">
			<li><button type="submit" name="newsession" value="New Session" class="btn btn-link btn-sm"><la:message key="labels.automl_new_session" /></button></li>
			<li><button type="submit" name="deleteproject" value="Delete Project" class="btn btn-link btn-sm"><la:message key="labels.automl_delete_project" /></button></li>
		</ul>
	</div>
</div>
</form>