<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.easyml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="brandName" value="Fione" />
			<jsp:param name="logoPath" value="/images/fione/logo-head.png" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="easyml" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>
								<la:message key="labels.easyml_project_dashboard" />
							</h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
							</ol>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<div class="row">
					<div class="col-md-3">
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title">
									<la:message key="labels.easyml_projects" />
								</h3>
								<div class="btn-tools pull-right">
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(projects) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(projects) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped">
												<thead>
													<tr>
														<th><la:message key="labels.automl_name" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${projects}">
														<tr data-href="${contextPath}/admin/easyml/job/${f:u(data.id)}">
															<td>${f:h(data.name)}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
					</div>
					<div class="col-md-9">
						<la:form action="/admin/easyml/uploaddataset" enctype="multipart/form-data">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.easyml_new_project" /></h3>
									<div class="btn-tools pull-right">
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
										<label for="name" class="col-sm-3 col-form-label"><la:message key="labels.easyml_project_name" /></label>
										<div class="col-sm-9">
											<la:errors property="name" />
											<la:text styleId="name" property="name" styleClass="form-control" />
										</div>
									</div>
									<div class="form-group row">
										<label for="file" class="col-sm-3 col-form-label"><la:message key="labels.easyml_training_data" /></label>
										<div class="col-sm-9">
											<la:errors property="file" />
											<input type="file" name="file" class="form-control-file"/>
										</div>
									</div>
								</div>
								<div class="card-footer">
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success">
											<em class="fa fa-plus"></em>
											<la:message key="labels.crud_button_create" />
										</button>
									</c:if>
								</div>
							</div>
						</la:form>
					</div>
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
