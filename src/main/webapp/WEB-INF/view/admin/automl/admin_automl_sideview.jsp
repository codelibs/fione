<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%><%@taglib prefix="fi"
	uri="http://fione.codelibs.org/functions"
%>
<c:if test="${columnSummaries != null}">
	<div class="card card-outline card-primary">
		<div class="card-header">
			<h3 class="card-title">${f:h(fi:frameName(frameId))}</h3>
			<div class="card-tools">
				<button type="button" class="btn btn-tool" data-card-widget="collapse">
					<i class="fa fa-minus"></i>
				</button>
			</div>
		</div>
		<div class="card-body">
			<table class="table table-bordered table-striped">
				<tbody>
					<tr>
						<th><la:message key="labels.automl_rows" /></th>
						<td style="text-align: right;">${f:h(columnSummaries.rows)}</td>
					</tr>
					<tr>
						<th><la:message key="labels.automl_columns" /></th>
						<td style="text-align: right;">${f:h(columnSummaries.totalColumnCount)}</td>
					</tr>
					<tr>
						<th><la:message key="labels.automl_compressed_size" /></th>
						<td style="text-align: right;">${fe:formatFileSize(columnSummaries.byteSize)}</td>
					</tr>
				</tbody>
			</table>
		</div>
	</div>
</c:if>
<div class="card card-outline card-primary">
	<div class="card-header">
		<h3 class="card-title">
			<la:message key="labels.automl_datasets" />
		</h3>
		<div class="card-tools">
			<button type="button" class="btn btn-tool" data-card-widget="collapse">
				<i class="fa fa-minus"></i>
			</button>
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
								<th style="width: 35%"></th>
							</tr>
						</thead>
						<tbody>
							<c:forEach var="data" varStatus="s" items="${project.dataSets}">
								<tr>
									<form method="post" action="${contextPath}/admin/automl/">
										<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}"> <input
											type="hidden" name="projectId" value="${f:h(project.id)}"
										> <input type="hidden" name="dataSetId" value="${f:h(data.id)}"> <input type="hidden" name="frameId"
											value="${f:h(frameId)}"
										> <input type="hidden" name="leaderboardId" value="${f:h(leaderboardId)}">
										<td class="text-break"><c:choose>
												<c:when test="${data.type == 'train' and data.schema != null}">
													<button type="submit" name="datasettype" value="test" class="btn btn-link" style="padding: 0;">
														<i class="fas fa-chart-area" title="<la:message key="labels.automl_training_data" />"></i>
													</button>
												</c:when>
												<c:when test="${data.type == 'test'}">
													<button type="submit" name="datasettype" value="train" class="btn btn-link" style="padding: 0;">
														<i class="fas fa-chart-bar" title="<la:message key="labels.automl_test_data" />"></i>
													</button>
												</c:when>
												<c:when test="${data.type == 'predict'}">
													<button type="submit" name="datasettype" value="train" class="btn btn-link" style="padding: 0;">
														<i class="fas fa-chart-line" title="<la:message key="labels.automl_predicted_data" />"></i>
													</button>
												</c:when>
												<c:otherwise>
													<em class="fas fa-question" style="color: #337ab7;" title="<la:message key="labels.automl_unknown" />"></em>
												</c:otherwise>
											</c:choose> ${f:h(data.name)}</td>
										<td class="text-center"><c:if test="${data.schema != null}">
												<la:link href="/admin/automl/newframe/${f:u(project.id)}/${f:u(data.id)}">
													<i class="fas fa-table" title="<la:message key="labels.automl_create_frame" />"></i>
												</la:link>
											</c:if> <c:if test="${data.schema == null}">
												<button type="submit" name="loaddataset" value="load" class="btn btn-link" style="padding: 0;">
													<i class="fas fa-sync" title="<la:message key="labels.automl_load_schema" />"></i>
												</button>
											</c:if>
											<button type="submit" name="downloaddataset" value="download" class="btn btn-link" style="padding: 0;">
												<i class="fas fa-download" title="<la:message key="labels.automl_download" />"></i>
											</button>
											<button type="submit" name="deletedataset" value="Delete" class="btn btn-link" style="padding: 0;">
												<i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i>
											</button></td>
									</form>
								</tr>
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
		<h3 class="card-title">
			<la:message key="labels.automl_frames" />
		</h3>
		<div class="card-tools">
			<button type="button" class="btn btn-tool" data-card-widget="collapse">
				<i class="fa fa-minus"></i>
			</button>
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
								<th style="width: 35%"></th>
							</tr>
						</thead>
						<tbody>
							<c:forEach var="data" varStatus="s" items="${project.frameIds}">
								<tr>
									<form method="post" action="${contextPath}/admin/automl/">
										<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}"> <input
											type="hidden" name="projectId" value="${f:h(project.id)}"
										> <input type="hidden" name="frameId" value="${f:h(data)}"> <input type="hidden"
											name="leaderboardId" value="${f:h(leaderboardId)}"
										>
										<td>${f:h(fi:frameName(data))}</td>
										<td class="text-center"><c:if test="${frameId == data}">
												<i class="far fa-check-square" style="color: #3c8dbc;"></i>
											</c:if> <c:if test="${frameId != data}">
												<la:link href="/admin/automl/job/${f:u(project.id)}?fid=${f:u(data)}&lid=${f:u(leaderboardId)}">
													<i class="far fa-square"></i>
												</la:link>
											</c:if>
											<button type="submit" name="deleteframe" value="Delete" class="btn btn-link" style="padding: 0;">
												<i class="fas fa-trash-alt" title="<la:message key="labels.automl_delete" />"></i>
											</button></td>
									</form>
								</tr>
							</c:forEach>
						</tbody>
					</table>
				</div>
			</div>
		</c:if>
	</div>
</div>
<c:if test="${fn:length(leaderboardIds) gt 0}">
	<div class="card card-outline card-primary">
		<div class="card-header">
			<h3 class="card-title">
				<la:message key="labels.automl_modelset" />
			</h3>
			<div class="card-tools">
				<button type="button" class="btn btn-tool" data-card-widget="collapse">
					<i class="fa fa-minus"></i>
				</button>
			</div>
		</div>
		<div class="card-body">
			<div class="row">
				<div class="col-sm-12">
					<table class="table table-bordered table-striped">
						<thead>
							<tr>
								<th><la:message key="labels.automl_name" /></th>
								<th style="width: 35%"></th>
							</tr>
						</thead>
						<tbody>
							<c:forEach var="data" varStatus="s" items="${leaderboardIds}">
								<tr>
									<form method="post" action="${contextPath}/admin/automl/">
										<input type="hidden" name="lastaflute.action.TRANSACTION_TOKEN" value="${f:h(token)}"> <input
											type="hidden" name="projectId" value="${f:h(project.id)}"
										> <input type="hidden" name="frameId" value="${f:h(frameId)}"> <input type="hidden"
											name="leaderboardId" value="${f:h(data)}"
										>
										<td>${f:h(fi:frameName(data))}</td>
										<td class="text-center"><c:if test="${leaderboardId == data}">
												<i class="far fa-check-square" style="color: #3c8dbc;"></i>
											</c:if> <c:if test="${leaderboardId != data}">
												<la:link href="/admin/automl/job/${f:u(project.id)}?fid=${f:u(frameId)}&lid=${f:u(data)}">
													<i class="far fa-square"></i>
												</la:link>
											</c:if>
									</form>
								</tr>
							</c:forEach>
						</tbody>
					</table>
				</div>
			</div>
		</div>
	</div>
</c:if>
