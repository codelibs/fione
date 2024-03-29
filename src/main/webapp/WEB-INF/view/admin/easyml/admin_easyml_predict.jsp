<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi"
	uri="http://fione.codelibs.org/functions"
%><!DOCTYPE html>
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
							<h1><la:message key="labels.easyml_new_prediction" arg0="${f:h(project.name)}" /></h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="../dataset">
									<la:message key="labels.easyml_dataset" />
								</la:link></li>
								<li class="breadcrumb-item"><la:link href="../train/${f:u(projectId)}?did=${f:u(dataSetId)}">
									<la:message key="labels.easyml_data_analysis" />
								</la:link></li>
								<li class="breadcrumb-item"><la:link href="../summary/${f:u(projectId)}?did=${f:u(dataSetId)}&lid=${f:u(leaderboardId)}">
									<la:message key="labels.easyml_summary" />
								</la:link></li>
								<li class="breadcrumb-item active"><la:message key="labels.easyml_prediction" /></li>
							</ol>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<la:form action="/admin/easyml/uploadprediction" enctype="multipart/form-data">
							<la:hidden property="projectId"/>
							<la:hidden property="dataSetId"/>
							<la:hidden property="leaderboardId"/>
							<div class="card card-outline card-success">
								<div class="card-header">
									<h3 class="card-title">
										<la:message key="labels.easyml_upload_dataset" />
									</h3>
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
										<label for="name" class="col-sm-3 col-form-label"><la:message key="labels.easyml_name" /></label>
										<div class="col-sm-9">
											<la:errors property="name" />
											<la:text property="name" styleId="name" styleClass="form-control"/>
										</div>
									</div>
									<div class="form-group row">
										<label for="file" class="col-sm-3 col-form-label"><la:message key="labels.easyml_prediction_data" /></label>
										<div class="col-sm-9">
											<la:errors property="file" />
											<input type="file" name="file" class="form-control-file"/>
										</div>
									</div>
									<div class="form-group row">
										<label for="columnNames" class="col-sm-3 col-form-label"><la:message key="labels.easyml_output_columns" /></label>
										<div class="col-sm-9">
											<la:errors property="columnNames" />
											<la:select property="columnNames" styleId="columnNames" multiple="true" styleClass="form-control">
												<c:forEach var="item" items="${columnItems}">
													<la:option value="${f:u(item.value)}">${f:h(item.label)}</la:option>
												</c:forEach>
											</la:select>
										</div>
									</div>
								</div>
								<div class="card-footer">
									<la:link href="../summary/${f:u(projectId)}?did=${f:u(dataSetId)}&lid=${f:u(leaderboardId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="createproject"
											value="<la:message key="labels.crud_button_create" />"
										>
											<em class="fa fa-file-upload"></em>
											<la:message key="labels.easyml_upload" />
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
