<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi"
	uri="http://fione.codelibs.org/functions"
%><!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title><la:message key="labels.admin_brand_title" /> | <la:message key="labels.easyml" /></title>
<jsp:include page="/WEB-INF/view/common/admin/head.jsp"></jsp:include>
</head>
<body class="skin-blue sidebar-mini">
	<div class="wrapper">
		<jsp:include page="/WEB-INF/view/common/admin/header.jsp"></jsp:include>
		<jsp:include page="/WEB-INF/view/common/admin/sidebar.jsp">
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="easyml" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1><la:message key="labels.easyml_new_prediction" arg0="${f:h(project.name)}" /></h1>
				<ol class="breadcrumb">
					<li><la:link href="../dataset">
							<la:message key="labels.easyml_dataset" />
						</la:link></li>
					<li><la:link href="../train/${f:u(projectId)}?did=${f:u(dataSetId)}">
							<la:message key="labels.easyml_data_analysis" />
						</la:link></li>
					<li><la:link href="../summary/${f:u(projectId)}?did=${f:u(dataSetId)}&lid=${f:u(leaderboardId)}">
							<la:message key="labels.easyml_summary" />
						</la:link></li>
					<li class="active"><la:message key="labels.easyml_prediction" /></li>
				</ol>
			</section>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<la:form action="/admin/easyml/uploadprediction" styleClass="form-horizontal" enctype="multipart/form-data">
							<la:hidden property="projectId"/>
							<la:hidden property="dataSetId"/>
							<la:hidden property="leaderboardId"/>
							<div class="box box-success">
								<div class="box-header with-border">
									<h3 class="box-title">
										<la:message key="labels.easyml_upload_dataset" />
									</h3>
									<div class="btn-tools pull-right">
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
										<label for="file" class="col-sm-3 control-label"><la:message key="labels.easyml_prediction_data" /></label>
										<div class="col-sm-9">
											<la:errors property="file" />
											<input type="file" name="file" />
										</div>
									</div>
								</div>
								<div class="box-footer">
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
