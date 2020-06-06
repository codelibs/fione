<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi" uri="http://fione.codelibs.org/functions" %><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.fione_brand_title" /> | <la:message key="labels.systemml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="hold-transition skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="brandName" value="Fione" />
			<jsp:param name="logoPath" value="/images/fione/logo-head.png" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="systemml" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>
								<la:message key="labels.systemml_title_addmodule" />
							</h1>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<la:form action="/admin/systemml/uploadmodule" enctype="multipart/form-data">
					<div class="row">
						<div class="col-md-12">
							<div class="card card-outline card-success">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.systemml_add_module" /></h3>
									<div class="card-tools">
										<la:link href="/admin/systemml/" styleClass="btn btn-primary btn-xs">
											<em class="fas fa-project-diagram"></em>
											<la:message key="labels.systemml" />
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
										<label for="moduleFile" class="col-sm-3 col-form-label"><la:message key="labels.systemml_module_file" /></label>
										<div class="col-sm-9">
											<la:errors property="moduleFile" />
											<input type="file" name="moduleFile" class="form-control-file"/>
										</div>
									</div>
								</div>
								<div class="card-footer">
									<la:link href="/admin/systemml/" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="uploaddataset" value="Upload">
											<em class="fa fa-plus"></em>
											<la:message key="labels.systemml_upload" />
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
