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
			<jsp:param name="logoPath" value="/images/fione/logo-head.png" />
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<div class="content-header">
				<div class="container-fluid">
					<div class="row mb-2">
						<div class="col-sm-6">
							<h1>
								<la:message key="labels.automl_project_title" arg0="${f:h(project.name)}" />
							</h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="../list">
									<la:message key="labels.crud_link_list" />
								</la:link></li>
								<li class="breadcrumb-item active">${f:h(project.name)}</li>
							</ol>
						</div>
					</div>
				</div>
			</div>
			<section class="content">
				<div class="row">
					<div class="col-md-12">
						<la:info id="msg" message="true">
							<div class="alert alert-info">${msg}</div>
						</la:info>
						<la:errors />
						<div class="card card-outline">
							<div class="card-body p-2">
								<jsp:include page="/WEB-INF/view/admin/automl/admin_automl_toolbar.jsp"></jsp:include>
							</div>
						</div>
					</div>
					<div class="col-md-3">
						<jsp:include page="/WEB-INF/view/admin/automl/admin_automl_sideview.jsp"></jsp:include>
					</div>
					<div class="col-md-9">
						<c:if test="${columnSummaries != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_column_summaries" arg0="${f:h(fi:frameName(frameId))}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<%-- List --%>
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped small">
												<thead>
													<tr>
														<th><la:message key="labels.automl_label" /></th>
														<th><la:message key="labels.automl_type" /></th>
														<th><la:message key="labels.automl_missing" /></th>
														<th><la:message key="labels.automl_zeros" /></th>
														<th><la:message key="labels.automl_posinf" /></th>
														<th><la:message key="labels.automl_neginf" /></th>
														<th><la:message key="labels.automl_min" /></th>
														<th><la:message key="labels.automl_max" /></th>
														<th><la:message key="labels.automl_mean" /></th>
														<th><la:message key="labels.automl_sigma" /></th>
														<th><la:message key="labels.automl_cardinality" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${columnSummaries.columns}">
														<tr>
															<td>
															<la:link href="/admin/automl/columnview/${f:u(project.id)}/${f:u(data.label)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">${f:h(data.label)}</la:link>
															</td>
															<td>${f:h(data.type)}</td>
															<td>${f:h(data.missingCount)}</td>
															<td>${f:h(data.zeroCount)}</td>
															<td>${f:h(data.positiveInfinityCount)}</td>
															<td>${f:h(data.negativeInfinityCount)}</td>
															<td><fmt:formatNumber value="${data.mins[0]}" maxFractionDigits="6" /></td>
															<td><fmt:formatNumber value="${data.maxs[0]}" maxFractionDigits="6" /></td>
															<td><fmt:formatNumber value="${data.mean}" maxFractionDigits="6" /></td>
															<td><fmt:formatNumber value="${data.sigma}" maxFractionDigits="6" /></td>
															<td>${f:h(data.domainCardinality)}</td>
														</tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</div>
							</div>
						</c:if>
					</div>
				</div>
			</section>
		</div>
		<jsp:include page="/WEB-INF/view/common/admin/footer.jsp"></jsp:include>
	</div>
	<jsp:include page="/WEB-INF/view/common/admin/foot.jsp"></jsp:include>
</body>
</html>
