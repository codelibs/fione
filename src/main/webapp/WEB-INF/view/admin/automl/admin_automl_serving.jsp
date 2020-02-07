<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1>${f:h(model.modelId.name)}</h1>
				<ol class="breadcrumb">
					<li><la:link href="/admin/automl">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li><la:link href="/admin/automl/details/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">
							<la:message key="labels.automl_project" />
						</la:link></li>
					<li class="active"><la:message key="labels.automl_model" /></li>
				</ol>
			</section>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<la:info id="msg" message="true">
							<div class="alert alert-info">${msg}</div>
						</la:info>
						<la:errors />
					</div>
					<div class="col-md-12">
					<form method="post" action="${contextPath}/admin/automl/">
						<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
						<input type="hidden" name="projectId" value="${f:h(projectId)}">
						<input type="hidden" name="modelId" value="${f:h(model.modelId.name)}">
						<input type="hidden" name="frameId" value="${f:h(frameId)}">
						<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
						<div class="btn-group" role="toolbar" aria-label="Toolbar" style="margin-bottom:5px;">
							<button type="submit" name="downloadserving" value="load" class="btn btn-default"><i class="fab fa-docker"></i><la:message key="labels.automl_download" /></button>
							<la:link href="/admin/automl/model/${f:u(projectId)}/${f:u(model.modelId.name)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-default"><i class="fas fa-hammer"></i><la:message key="labels.automl_model" /></la:link>
							<la:link href="/admin/automl/details/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-default"><i class="fas fa-project-diagram"></i><la:message key="labels.automl_model_project" /></la:link>
						</div>
						<div class="card-tools" role="toolbar" aria-label="Toolbar" style="margin-bottom:5px;">
							<button type="submit" name="deletemodel" value="load" class="btn btn-default"><i class="fas fa-trash-alt"></i><la:message key="labels.automl_delete" /></button>
						</div>
						</form>
					</div>
					<div class="col-md-12">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_serving_with_docker" /></h3>
								<div class="btn-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse">
										<i class="fa fa-minus"></i>
									</button>
								</div>
							</div>
							<div class="card-body">
							<h3><la:message key="labels.automl_download_zip_file" /></h3>
							<p><la:message key="labels.automl_download_dockerfile" /></p>
							<h3><la:message key="labels.automl_build_dockerimage" /></h3>
							<p><la:message key="labels.automl_contain_dockerfile" arg0="${f:h(dockerZipName)}" /></p>
<pre><code>$ unzip ${f:h(dockerZipName)}
$ cd serving
$ docker build -t ${f:h(dockerTagName)}/serving:1.0 .</code></pre>
							<h3><la:message key="labels.automl_run_serving_api" /></h3>
							<p><la:message key="labels.automl_start_serving_container" /></p>
<pre><code>$ docker run -t --rm -p 8081:8080 -t ${f:h(dockerTagName)}/serving:1.0 &</code></pre>
							<h3><la:message key="labels.automl_access_predict_api" /></h3>
							<p><la:message key="labels.automl_query_predict_api" /></p>
<pre><code>$ curl -XPOST -H "Content-Type: application/json" localhost:8081/invocations -d '{
  "instances": [
    <c:if test="${instance!=null}">${f:h(instance)}</c:if><c:if test="${instance==null}">{...instance object...}</c:if>
  ]
}'</code></pre>
							<p><la:message key="labels.automl_show_model_info" /></p>
<pre><code>$ curl -s -XGET -H "Content-Type: application/json" localhost:8081/model</code></pre>
							</div>
						</div>
					</div>
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
