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
			<jsp:param name="brandName" value="Fione" />
			<jsp:param name="logoPath" value="${fe:url('/images/fione/logo-head.png')}" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1><la:message key="labels.automl_moudule_configuration" /></h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="/admin/automl">
									<la:message key="labels.crud_link_list" />
								</la:link></li>
								<li class="breadcrumb-item"><la:link href="/admin/automl/job/${f:u(projectId)}">
									<la:message key="labels.automl_project" />
								</la:link></li>
								<li class="breadcrumb-item active"><la:message key="labels.automl_moudule_configuration" /></li>
							</ol>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<la:form action="/admin/automl" >
					<la:hidden property="projectId" />
					<la:hidden property="moduleId" />
					<la:hidden property="frameId" />
					<la:hidden property="modelId" />
					<div class="row">
						<div class="col-md-12">
							<div class="card card-outline card-success">
								<div class="card-header">
									<h3 class="card-title">${f:h(module.name)}</h3>
									<div class="card-tools">
										<la:link href="/admin/automl/job/${f:u(projectId)}" styleClass="btn btn-primary btn-xs">
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
									<c:if test="${module.type eq 'FRAME'}">
									<div class="form-group row">
										<label for="frameId" class="col-sm-3 col-form-label"><la:message key="labels.automl_module_frameid" /></label>
										<div class="col-sm-9">
											${f:h(fi:jobName(frameId))}
										</div>
									</div>
									</c:if>
									<c:if test="${module.type eq 'PREDICT'}">
									<div class="form-group row">
										<label for="modelId" class="col-sm-3 col-form-label"><la:message key="labels.automl_module_modelid" /></label>
										<div class="col-sm-9">
											${f:h(fi:jobName(modelId))}
										</div>
									</div>
									</c:if>
									<c:forEach var="c" items="${module.components}">
									<div class="form-group row">
										<label for="${f:u(c.id)}" class="col-sm-3 col-form-label">${f:h(c.name)}</label>
										<div class="col-sm-9">
											<c:choose>
											<c:when test="${c.type == 'COLUMN'}">
											<select name="params.${f:u(c.id)}" id="${f:u(c.id)}" class="form-control">
												<c:forEach var="item" items="${columnItems}">
													<option value="${f:u(item.value)}">${f:h(item.label)}</option>
												</c:forEach>
											</select>
											</c:when>
											<c:otherwise>
											<input type="text" name="params.${f:u(c.id)}" value="${f:u(c.value)}" id="${f:u(c.id)}" class="form-control">
											</c:otherwise>
											</c:choose>
											<c:if test="${not empty c.description}"><small class="form-text text-muted">${f:h(c.description)}</small></c:if>
										</div>
									</div>
									</c:forEach>
								</div>
								<div class="card-footer">
									<la:link href="/admin/automl/job/${f:u(projectId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="runmodule" value="Run">
											<em class="fas fa-hammer"></em> <la:message key="labels.automl_module_run" />
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
