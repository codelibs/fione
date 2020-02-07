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
			<jsp:param name="menuCategoryType" value="fione" />
			<jsp:param name="menuType" value="automl" />
		</jsp:include>
		<div class="content-wrapper">
			<section class="content-header">
				<h1>
					<la:message key="labels.automl_dataview_title" arg0="${f:h(project.name)}" />
				</h1>
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
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_actions" /></h3>
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="card-body">
								<div class="row">
									<form method="post" action="${contextPath}/admin/automl/">
									<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
									<input type="hidden" name="projectId" value="${f:h(project.id)}">
									<div class="btn-group-vertical col-sm-12" role="group" aria-label="Actions">
										<c:if test="${not empty frameId}">
										<div class="input-group">
											<span class="input-group-addon" id="basic-addon1"><i class="fas fa-table"></i></span>
											<span class="form-control">${f:h(fi:frameName(frameId))}</span>
										</div>
										</c:if>
										<c:if test="${not empty frameId and leaderboard != null}">
										<div class="input-group">
											<span class="input-group-addon" id="basic-addon1"><i class="fas fa-hammer"></i></span>
											<span class="form-control">${f:h(leaderboardId)}</span>
										</div>
										</c:if>
										<la:link href="/admin/automl/details/${f:u(project.id)}" styleClass="btn btn-default">
											<em class="fas fa-project-diagram"></em>
											<la:message key="labels.automl_project" />
										</la:link>
									</div>
									</form>
								</div>
							</div>
						</div>
						<c:if test="${columnSummaries != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title">${f:h(fi:frameName(frameId))}</h3>
									<div class="box-tools pull-right">
										<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
									</div>
								</div>
								<div class="card-body">
									<table class="table table-bordered table-striped">
										<tbody>
											<tr>
												<th><la:message key="labels.automl_rows" /></th>
												<td style="text-align:right;">${f:h(columnSummaries.rows)}</td>
											</tr>
											<tr>
												<th><la:message key="labels.automl_columns" /></th>
												<td style="text-align:right;">${f:h(columnSummaries.totalColumnCount)}</td>
											</tr>
											<tr>
												<th><la:message key="labels.automl_compressed_size" /></th>
												<td style="text-align:right;">${fe:formatFileSize(columnSummaries.byteSize)}</td>
											</tr>
										</tbody>
									</table>
								</div>
							</div>
						</c:if>
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_datasets" /></h3>
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(project.dataSets) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
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
														<th style="width: 30%" class=" text-center"><la:message key="labels.automl_action" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.dataSets}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="dataSetId" value="${f:h(data.id)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
															<td>
															<c:choose>
															<c:when test="${data.type == 'train' and data.schema != null}">
															<button type="submit" name="datasettype" value="test" class="btn btn-link" style="padding:0;"><i class="fas fa-chart-area" title="<la:message key="labels.automl_training_data" />"></i></button>
															</c:when>
															<c:when test="${data.type == 'test'}">
															<button type="submit" name="datasettype" value="train" class="btn btn-link" style="padding:0;"><i class="fas fa-chart-bar" title="<la:message key="labels.automl_test_data" />"></i></button>
															</c:when>
															<c:when test="${data.type == 'predict'}">
															<button type="submit" name="datasettype" value="train" class="btn btn-link" style="padding:0;"><i class="fas fa-chart-line" title="<la:message key="labels.automl_predicted_data" />"></i></button>
															</c:when>
															<c:otherwise><em class="fas fa-question" style="color:#337ab7;" title="<la:message key="labels.automl_unknown" />"></em></c:otherwise>
															</c:choose>
															${f:h(data.name)}</td>
															<td class="text-center">
															<c:if test="${data.schema != null}">
															<la:link href="/admin/automl/newframe/${f:u(project.id)}/${f:u(data.id)}"><i class="fas fa-table" title="<la:message key="labels.automl_create_frame" />"></i></la:link>
															</c:if>
															<c:if test="${data.schema == null}">
															<button type="submit" name="loaddataset" value="load" class="btn btn-link" style="padding:0;"><i class="fas fa-sync" title="<la:message key="labels.automl_load_schema" />"></i></button>
															</c:if>
															<button type="submit" name="downloaddataset" value="download" class="btn btn-link" style="padding:0;"><i class="fas fa-download" title="<la:message key="labels.automl_download" />"></i></button>
															<button type="submit" name="deletedataset" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i></button>
															</td>
														</form></tr>
													</c:forEach>
												</tbody>
											</table>
										</div>
									</div>
								</c:if>
							</div>
						</div>
						<div class="card card-outline card-primary">
							<div class="card-header">
								<h3 class="card-title"><la:message key="labels.automl_frames" /></h3>
								<div class="box-tools pull-right">
									<button type="button" class="btn btn-box-tool" data-widget="collapse"><i class="fa fa-minus"></i></button>
								</div>
							</div>
							<div class="card-body">
								<c:if test="${fn:length(project.frameIds) == 0}">
									<div class="row top10">
										<div class="col-sm-12">
											<em class="fa fa-info-circle text-primary"></em>
											<la:message key="labels.list_could_not_find_crud_table" />
										</div>
									</div>
								</c:if>
								<c:if test="${fn:length(project.frameIds) gt 0}">
									<div class="row">
										<div class="col-sm-12">
											<table class="table table-bordered table-striped">
												<thead>
													<tr>
														<th><la:message key="labels.automl_name" /></th>
														<th style="width: 25%" class="text-center"><la:message key="labels.automl_action" /></th>
													</tr>
												</thead>
												<tbody>
													<c:forEach var="data" varStatus="s" items="${project.frameIds}">
														<tr><form method="post" action="${contextPath}/admin/automl/">
														<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}">
														<input type="hidden" name="projectId" value="${f:h(project.id)}">
														<input type="hidden" name="frameId" value="${f:h(frameId)}">
														<input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
															<td>${f:h(fi:frameName(data))}</td>
															<td class="text-center">
															<c:if test="${frameId == data}"><i class="far fa-check-square" style="color:#3c8dbc;"></i></c:if>
															<c:if test="${frameId != data}"><la:link href="/admin/automl/dataview/${f:u(project.id)}?fid=${f:u(data)}&lid=${f:u(leaderboardId)}"><i class="far fa-square"></i></la:link></c:if>
															<button type="submit" name="deleteframe" value="Delete" class="btn btn-link" style="padding:0;"><i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i></button>
															</td>
														</form></tr>
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
						<c:if test="${frameData != null}">
							<div class="card card-outline card-primary">
								<div class="card-header">
									<h3 class="card-title"><la:message key="labels.automl_data_summaries" arg0="${f:h(fi:frameName(frameId))}" /></h3>
									<div class="box-tools pull-right">
										<span class="badge bg-info"><la:message key="labels.automl_data_and_column" arg0="${f:h(frameData.rowOffset+1)}" arg1="${f:h(frameData.columnOffset+1)}" /></span>
										<c:if test="${frameData.columnOffset > 0}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset)}&data.column_offset=${f:u(frameData.columnOffset-20)}" class="btn btn-box-tool"><i class="fas fa-arrow-left"></i></a></c:if>
										<c:if test="${frameData.columnOffset + 20 < frameData.numColumns}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset)}&data.column_offset=${f:u(frameData.columnOffset+20)}" class="btn btn-box-tool"><i class="fas fa-arrow-right"></i></a></c:if>
										<c:if test="${frameData.rowOffset > 0}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset-20)}&data.column_offset=${f:u(frameData.columnOffset)}" class="btn btn-box-tool"><i class="fas fa-arrow-up"></i></a></c:if>
										<c:if test="${frameData.rowOffset + 20 < frameData.rows}"><a href="${contextPath}/admin/automl/dataview/${f:u(project.id)}/?fid=${f:u(frameId)}&lid=${f:u(leaderboardId)}&data.row_offset=${f:u(frameData.rowOffset+20)}&data.column_offset=${f:u(frameData.columnOffset)}" class="btn btn-box-tool"><i class="fas fa-arrow-down"></i></a></c:if>
										<button type="button" class="btn btn-box-tool" data-widget="collapse">
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
														<c:forEach var="data" varStatus="s" begin="0" end="${frameData.rowSize}">
															<tr>
																<c:forEach var="data" varStatus="x" items="${frameData.row}">
																	<td>${f:h(data)}</td>
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
