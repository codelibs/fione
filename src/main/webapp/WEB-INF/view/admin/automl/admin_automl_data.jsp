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
								<la:message key="labels.automl_dataview_title" arg0="${f:h(project.name)}" />
							</h1>
						</div>
						<div class="col-sm-6">
							<ol class="breadcrumb float-sm-right">
								<li class="breadcrumb-item"><la:link href="../list">
									<la:message key="labels.crud_link_list" />
								</la:link></li>
								<li class="breadcrumb-item"><la:link href="/admin/automl/job/${f:u(project.id)}">
									${f:h(project.name)}
								</la:link></li>
								<li class="breadcrumb-item active"><la:message key="labels.automl_dataview" /></li>
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
						<c:if test="${frameData != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_data_summaries" arg0="${f:h(fi:frameName(frameId))}" /></h3>
									<div class="card-tools">
										<span class="badge bg-info"><la:message key="labels.automl_data_and_column" arg0="${f:h(frameData.rowOffset+1)}" arg1="${f:h(frameData.columnOffset+1)}" /></span>
										<c:if test="${frameData.columnOffset > 0}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset)}&data.column_offset=${f:u(frameData.columnOffset-20)}" class="btn btn-box-tool"><i class="fas fa-arrow-left"></i></a></c:if>
										<c:if test="${frameData.columnOffset + 20 < frameData.numColumns}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset)}&data.column_offset=${f:u(frameData.columnOffset+20)}" class="btn btn-box-tool"><i class="fas fa-arrow-right"></i></a></c:if>
										<c:if test="${frameData.rowOffset > 0}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset-20)}&data.column_offset=${f:u(frameData.columnOffset)}" class="btn btn-box-tool"><i class="fas fa-arrow-up"></i></a></c:if>
										<c:if test="${frameData.rowOffset + 20 < frameData.rows}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset+20)}&data.column_offset=${f:u(frameData.columnOffset)}" class="btn btn-box-tool"><i class="fas fa-arrow-down"></i></a></c:if>
										<button type="button" class="btn btn-tool" data-card-widget="collapse">
											<i class="fa fa-minus"></i>
										</button>
									</div>
								</div>
								<div class="card-body">
									<%-- List --%>
									<c:if test="${frameData.rows == 0}">
										<div class="row top10">
											<div class="col-sm-12">
												<em class="fa fa-info-circle text-primary"></em>
												<la:message key="labels.list_could_not_find_crud_table" />
											</div>
										</div>
									</c:if>
									<c:if test="${frameData.rows gt 0}">
										<div class="row">
											<div class="col-sm-12">
												<table class="table table-bordered table-striped small">
													<thead>
														<tr>
															<c:forEach var="data" varStatus="s" items="${frameData.columnNames}">
																<th>${f:h(data)}</th>
															</c:forEach>
														</tr>
													</thead>
													<tbody>
														<c:forEach var="row" varStatus="s" items="${frameData.dataRows}">
															<tr>
																<c:forEach var="v" varStatus="x" items="${row}">
																	<td>${f:h(v)}</td>
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
