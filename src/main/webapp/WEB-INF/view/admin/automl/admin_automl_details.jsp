<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><!DOCTYPE html>
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
				<h1>Project: ${f:h(project.name)}</h1>
				<ol class="breadcrumb">
					<li><la:link href="../list">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li class="active">${f:h(project.name)}</li>
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
					<div class="col-md-3">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Data List</h3>
								<div class="btn-group pull-right">
									<la:link href="/admin/automl/newdataset/${f:u(project.id)}"
										styleClass="btn btn-success btn-xs ${f:h(editableClass)}"
									>
										<em class="fa fa-plus"></em>
										Add
									</la:link>
								</div>
							</div>
							<div class="box-body">
								<c:if test="${fn:length(project.dataSets) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(project.dataSets) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped">
												<thead>
													<tr>
														<th><la:message key="labels.automl_name" /></th>
														<th class="col-sm-3">Status</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.dataSets}">
														<c:if test="${data.status == 'UNLOAD'}">
															<tr data-href="${contextPath}/admin/automl/importfile/${f:u(project.id)}/${f:u(data.id)}">
														</c:if>
														<c:if test="${data.status != 'UNLOAD'}">
															<tr data-href="${contextPath}/admin/automl/details/${f:u(project.id)}?dataSetId=${f:u(data.id)}">
														</c:if>
														<td>${f:h(data.name)}</td>
														<td class="text-center"><c:if test="${data.status == 'UNLOAD'}">
																<span class="label label-warning">${f:h(data.status)}</span>
															</c:if> <c:if test="${data.status != 'UNLOAD'}">
																<span class="label label-info">${f:h(data.status)}</span>
															</c:if></td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">Models</h3>
								<div class="btn-group pull-right">
									<c:if test="${dataSet.status == 'PARSED'}">
										<la:link href="/admin/automl/setupml/${f:u(project.id)}/${f:u(dataSet.id)}"
											styleClass="btn btn-success btn-xs ${f:h(editableClass)}"
										>
											<em class="fa fa-plus"></em>
										Run
									</la:link>
									</c:if>
								</div>
							</div>
							<div class="box-body">TODO</div>
						</div>
						<c:if test="${dataSet != null}">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">${f:h(dataSet.name)}</h3>
									<div class="btn-group pull-right">
										<c:if test="${dataSet.status == 'LOADED'}">
											<la:link href="/admin/automl/parsedata/${f:u(project.id)}/${f:u(dataSet.id)}"
												styleClass="btn btn-success btn-xs ${f:h(editableClass)}"
											>
												<em class="fas fa-glasses"></em>
												Parse
									</la:link>
										</c:if>
									</div>
								</div>
								<div class="box-body">
									<c:if test="${dataSet.meta == null}">Not parsed.</c:if>
									<c:if test="${dataSet.meta != null}">
										<table class="table table-bordered table-striped">
											<thead>
												<tr>
													<th>Field</th>
													<th>Type</th>
												</tr>
											</thead>
											<tbody>
												<c:forEach var="column" varStatus="s" items="${dataSet.meta.columnNames}">
													<tr>
														<td>${f:h(column)}</td>
														<td>${f:h(dataSet.meta.columnTypes[s.index])}</td>
													</tr>
												</c:forEach>
											</tbody>
										</table>
									</c:if>
								</div>
							</div>
						</c:if>
					</div>
					<c:if test="${columnSummaries != null}">
						<div class="col-md-9">
							<div class="box box-primary">
								<div class="box-header with-border">
									<h3 class="box-title">Column Summaries</h3>
								</div>
								<div class="box-body">
									<%-- List --%>
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th>Label</th>
														<th>Type</th>
														<th>Missing</th>
														<th>Zeros</th>
														<th>+Inf.</th>
														<th>-Inf.</th>
														<th>min</th>
														<th>max</th>
														<th>mean</th>
														<th>sigma</th>
														<th>Card.</th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${columnSummaries.columns}">
														<tr>
															<td>${f:h(data.label)}</td>
															<td>${f:h(data.type)}</td>
															<td>${f:h(data.missingCount)}</td>
															<td>${f:h(data.zeroCount)}</td>
															<td>${f:h(data.positiveInfinityCount)}</td>
															<td>${f:h(data.negativeInfinityCount)}</td>
															<td>${f:h(data.mins[0])}</td>
															<td>${f:h(data.maxs[0])}</td>
															<td>${f:h(data.mean)}</td>
															<td>${f:h(data.sigma)}</td>
															<td>${f:h(data.domainCardinality)}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</div>
							</div>
						</div>
					</c:if>
					<div class="col-md-9">
						<div class="box box-primary">
							<div class="box-header with-border">
								<h3 class="box-title">TODO</h3>
							</div>
							<div class="box-body">
								<%-- List --%>
								<c:if test="${fn:length(projects) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-light-blue"></em>
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
														<tr data-href="${contextPath}/admin/user/details/4/${f:u(data.id)}">
															<td>${f:h(data.id)}</td>
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
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
