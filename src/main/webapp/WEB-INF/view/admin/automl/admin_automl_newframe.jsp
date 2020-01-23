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
				<h1><la:message key="labels.automl_new_frame" /></h1>
				<ol class="breadcrumb">
					<li><la:link href="/admin/automl">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li><la:link href="/admin/automl/details/${f:u(projectId)}">
							<la:message key="labels.automl_project" />
						</la:link></li>
					<li class="active"><la:message key="labels.automl_new_frame" /></li>
				</ol>
			</section>
			<section class="content">
				<la:form action="/admin/automl" styleClass="form-horizontal">
					<la:hidden property="projectId"/>
					<la:hidden property="dataSetId"/>
					<div class="row">
						<div class="col-md-12">
							<div class="box box-success">
								<div class="box-header with-border">
									<h3 class="box-title">
										<la:message key="labels.crud_title_create" />
									</h3>
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
									<h4><la:message key="labels.automl_columns" /></h4>
									<c:forEach var="item" varStatus="s" items="${columnItems}">
									<div class="form-group">
										<label for="${f:u(item.id)}" class="col-sm-3 control-label">${f:h(item.name)}</label>
										<div class="col-sm-9">
											<select name="columns.${f:u(item.id)}" id="columns.${f:u(item.id)}" class="form-control">
											<c:forEach var="colType" items="${columnTypeItems}">
												<option value="${f:u(colType.value)}" <c:if test="${colType.value == item.value}">selected</c:if>>${f:h(colType.label)}</option>
											</c:forEach>
											</select>
										</div>
									</div>
									</c:forEach>
								</div>
								<div class="box-footer">
									<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="createframe"
											value="<la:message key="labels.crud_button_create" />"
										>
											<em class="fa fa-plus"></em>
											<la:message key="labels.crud_button_create" />
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
