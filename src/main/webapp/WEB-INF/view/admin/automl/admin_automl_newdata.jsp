<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.admin_brand_title" /> | <la:message key="labels.automl" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1><la:message key="labels.automl_upload_dataset" /></h1>
				<ol class="breadcrumb">
					<li><la:link href="/admin/automl">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li><la:link href="/admin/automl/details/${f:u(projectId)}">
							<la:message key="labels.automl_project" />
						</la:link></li>
					<li class="active"><la:message key="labels.automl_upload_dataset" /></li>
				</ol>
			</section>
			<section class="content">
				<la:form action="/admin/automl/uploaddataset" styleClass="form-horizontal" enctype="multipart/form-data">
					<la:hidden property="projectId" />
					<div class="row">
						<div class="col-md-12">
							<div class="box box-success">
								<div class="box-header with-border">
									<h3 class="box-title"><la:message key="labels.automl_new_dataset" /></h3>
									<div class="btn-group pull-right">
										<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-primary btn-xs">
											<em class="fas fa-project-diagram"></em>
											<la:message key="labels.automl_project" />
										</la:link>
									</div>
								</div>
								<div class="box-body">
									<div>
										<la:info id="msg" message="true">
											<div class="alert alert-info">${msg}</div>
										</la:info>
										<la:errors property="_global" />
									</div>
									<div class="form-group">
										<label for="dataFile" class="col-sm-3 control-label"><la:message key="labels.automl_data_file" /></label>
										<div class="col-sm-9">
											<la:errors property="dataFile" />
											<input type="file" name="dataFile" />
										</div>
									</div>
								</div>
								<div class="box-footer">
									<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="uploaddataset" value="Upload">
											<em class="fa fa-plus"></em>
											<la:message key="labels.automl_upload" />
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
