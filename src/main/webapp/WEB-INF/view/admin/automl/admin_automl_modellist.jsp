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
						<c:if test="${leaderboard != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_model_summaries" arg0="${f:h(leaderboard.projectName)}" /></h3>
									<div class="card-tools">
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
										<button type="button" class="btn btn-box-tool dropdown-toggle" data-toggle="dropdown" aria-expanded="true">
											<i class="fas fa-th-list"></i>
										</button>
										<ul class="dropdown-menu" role="menu">
											<li><form method="post" action="${contextPath}/admin/automl/">
											<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
											<input type="hidden" name="projectId" value="${f:h(project.id)}">
											<input type="hidden" name="frameId" value="${f:h(frameId)}">
											<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
											<c:if test="${leaderboard.inLocal}">
												<button type="submit" name="deleteleaderboard" value="Delete Models" class="btn btn-link"><la:message key="labels.automl_delete_models" /></button>
											</c:if>
											<c:if test="${not leaderboard.inLocal}">
												<button type="submit" name="exportallmodels" value="Export All" class="btn btn-link"><la:message key="labels.automl_export_all" /></button>
											</c:if>
											</form></li>
										</ul>
									</div>
								</div>
								<div class="card-body">
									<%-- List --%>
									<c:if test="${fn:length(leaderboard.models) == 0}">
										<div class="row top10">
											<div class="col-sm-12">
												<em class="fa fa-info-circle text-primary"></em>
												<la:message key="labels.list_could_not_find_crud_table" />
											</div>
										</div>
									</c:if>
									<c:if test="${fn:length(leaderboard.models) gt 0}">
										<div class="row">
											<div class="col-sm-12">
												<table class="table table-bordered table-striped small">
													<thead>
														<tr>
															<c:forEach var="data" varStatus="s" items="${leaderboard.columnNames}">
																<th>${f:h(data)}</th>
															</c:forEach>
														</tr>
													</thead>
													<tbody>
														<c:forEach var="row" varStatus="s" items="${leaderboard.dataRows}">
															<tr>
																<c:forEach var="data" varStatus="x" items="${row}">
																	<c:if test="${x.index == 0}"><td><a href="${contextPath}/admin/automl/model/${f:u(project.id)}/${f:u(data)}?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}">${f:h(data)}</a></td></c:if>
																	<c:if test="${x.index != 0}"><td>${f:h(data)}</td></c:if>
																</c:forEach>
															</tr>
														</c:forEach>
													</tbody>
												</table>
											</div>
										</div>
									</c:if>
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
