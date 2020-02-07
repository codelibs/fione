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
				<h1><la:message key="labels.automl_prediction" /></h1>
				<ol class="breadcrumb">
					<li><la:link href="/admin/automl">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li><la:link href="/admin/automl/details/${f:u(projectId)}">
							<la:message key="labels.automl_project" />
						</la:link></li>
					<li class="active"><la:message key="labels.automl_prediction" /></li>
				</ol>
			</section>
			<section class="content">
				<la:form action="/admin/automl" >
					<la:hidden property="projectId" />
					<la:hidden property="frameId" />
					<la:hidden property="leaderboardId" />
					<div class="row">
						<div class="col-md-12">
							<div class="card card-outline card-success">
								<div class="card-header">
									<h3 class="card-title">
										<la:message key="labels.automl_prediction_for" arg0="${f:h(fi:frameName(frameId))}" />
									</h3>
									<div class="card-tools">
										<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-primary btn-xs">
											<em class="fas fa-project-diagram"></em>
											<la:message key="labels.automl_project" />
										</la:link>
									</div>
								</div>
								<div class="card-body">
									<div>
										<la:info id="msg" message="true">
											<div class="alert alert-info">${msg}</div>
										</la:info>
										<la:errors property="_global" />
									</div>
									<div class="form-group row">
										<label for="name" class="col-sm-3 col-form-label"><la:message key="labels.automl_prediction_name" /></label>
										<div class="col-sm-9">
											<la:errors property="name" />
											<la:text styleId="name" property="name" styleClass="form-control" />
										</div>
									</div>
									<div class="form-group row">
										<label for="modelId" class="col-sm-3 col-form-label"><la:message key="labels.automl_use_model" /></label>
										<div class="col-sm-9">
											<la:errors property="modelId" />
											<la:select property="modelId" styleId="modelId" styleClass="form-control">
												<c:forEach var="item" items="${modelIdItems}">
													<la:option value="${f:u(item)}">${f:h(item)}</la:option>
												</c:forEach>
											</la:select>
										</div>
									</div>
								</div>
								<div class="card-footer">
									<la:link href="/admin/automl/details/${f:u(projectId)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="predictframe"
											value="<la:message key="labels.crud_button_create" />"
										>
											<i class="fas fa-file-signature"></i>
											<la:message key="labels.automl_predict" />
										</button>
									</c:if>
								</div>
							</div>
						</div>
					</div>
				</la:form>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
