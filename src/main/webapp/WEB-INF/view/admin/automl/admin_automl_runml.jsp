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
				<h1>Run AutoML</h1>
				<ol class="breadcrumb">
					<li><la:link href="../list">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li class="active">Run AutoML</li>
				</ol>
			</section>
			<section class="content">
				<la:form action="/admin/automl" styleClass="form-horizontal">
					<la:hidden property="projectId" />
					<la:hidden property="frameId" />
					<div class="row">
						<div class="col-md-12">
							<div class="box box-success">
								<div class="box-header with-border">
									<h3 class="box-title">AutoML Settings</h3>
									<div class="btn-group pull-right">
										<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-primary btn-xs">
											<em class="fas fa-project-diagram"></em>
											Project
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
									<div class="form-group">
										<label for="responseColumn" class="col-sm-3 control-label">Predicted Column</label>
										<div class="col-sm-9">
											<la:errors property="responseColumn" />
											<la:select property="responseColumn" styleId="responseColumn" styleClass="form-control">
												<c:forEach var="item" items="${columnItems}">
													<la:option value="${f:u(item)}">${f:h(item)}</la:option>
												</c:forEach>
											</la:select>
										</div>
									</div>
									<div class="form-group">
										<label for="maxRuntimeSecs" class="col-sm-3 control-label">Max Runtime Secs</label>
										<div class="col-sm-9">
											<la:errors property="maxRuntimeSecs" />
											<input type="number" name="maxRuntimeSecs" id="maxRuntimeSecs" value="${f:h(maxRuntimeSecs)}"
												class="form-control" min="0"
											>
										</div>
									</div>
									<div class="collapse" id="advanceSettings">
										<div class="form-group">
											<label for="nfolds" class="col-sm-3 control-label">n Folds</label>
											<div class="col-sm-9">
												<la:errors property="nfolds" />
												<input type="number" name="nfolds" id="nfolds" value="${f:h(nfolds)}" class="form-control" min="0">
											</div>
										</div>
										<div class="form-group">
											<label for="balanceClasses" class="col-sm-3 control-label">Balance Classes</label>
											<div class="col-sm-9">
												<la:errors property="balanceClasses" />
												<la:select property="balanceClasses" styleId="balanceClasses" styleClass="form-control">
													<la:option value="true">True</la:option>
													<la:option value="false">False</la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="seed" class="col-sm-3 control-label">Seed</label>
											<div class="col-sm-9">
												<la:errors property="seed" />
												<input type="number" name="seed" id="seed" value="${f:h(seed)}" class="form-control">
											</div>
										</div>
										<div class="form-group">
											<label for="maxModels" class="col-sm-3 control-label">Max Models</label>
											<div class="col-sm-9">
												<la:errors property="seed" />
												<input type="number" name="maxModels" id="maxModels" value="${f:h(maxModels)}" class="form-control" min="0">
											</div>
										</div>
										<div class="form-group">
											<label for="maxRuntimeSecsPerModel" class="col-sm-3 control-label">Max Runtime Secs Per Model</label>
											<div class="col-sm-9">
												<la:errors property="maxRuntimeSecsPerModel" />
												<input type="number" name="maxRuntimeSecsPerModel" id="maxRuntimeSecsPerModel"
													value="${f:h(maxRuntimeSecsPerModel)}" class="form-control" min="0"
												>
											</div>
										</div>
										<div class="form-group">
											<label for="stoppingRounds" class="col-sm-3 control-label">Stopping Rounds</label>
											<div class="col-sm-9">
												<la:errors property="stoppingRounds" />
												<input type="number" name="stoppingRounds" id="stoppingRounds" value="${f:h(stoppingRounds)}"
													class="form-control" min="0"
												>
											</div>
										</div>
										<div class="form-group">
											<label for="stoppingMetric" class="col-sm-3 control-label">Stopping Metric</label>
											<div class="col-sm-9">
												<la:errors property="stoppingMetric" />
												<la:select property="stoppingMetric" styleId="stoppingMetric" styleClass="form-control">
													<c:forEach var="item" items="${stoppingMetricItems}">
														<la:option value="${f:u(item)}">${f:h(item)}</la:option>
													</c:forEach>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="stoppingTolerance" class="col-sm-3 control-label">Stopping Tolerance</label>
											<div class="col-sm-9">
												<la:errors property="stoppingTolerance" />
												<la:text styleId="stoppingTolerance" property="stoppingTolerance" styleClass="form-control" />
											</div>
										</div>
										<div class="form-group">
											<label for="keepCrossValidationPredictions" class="col-sm-3 control-label">Keep Cross Validation
												Predictions</label>
											<div class="col-sm-9">
												<la:errors property="keepCrossValidationPredictions" />
												<la:select property="keepCrossValidationPredictions" styleId="keepCrossValidationPredictions"
													styleClass="form-control"
												>
													<la:option value="true">True</la:option>
													<la:option value="false">False</la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="keepCrossValidationModels" class="col-sm-3 control-label">Keep Cross Validation Models</label>
											<div class="col-sm-9">
												<la:errors property="keepCrossValidationModels" />
												<la:select property="keepCrossValidationModels" styleId="keepCrossValidationModels"
													styleClass="form-control"
												>
													<la:option value="true">True</la:option>
													<la:option value="false">False</la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="keepCrossValidationFoldAssignment" class="col-sm-3 control-label">Keep Cross Validation
												Fold Assignment</label>
											<div class="col-sm-9">
												<la:errors property="keepCrossValidationFoldAssignment" />
												<la:select property="keepCrossValidationFoldAssignment" styleId="keepCrossValidationFoldAssignment"
													styleClass="form-control"
												>
													<la:option value="true">True</la:option>
													<la:option value="false">False</la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="sortMetric" class="col-sm-3 control-label">Sort Metric</label>
											<div class="col-sm-9">
												<la:errors property="sortMetric" />
												<la:select property="sortMetric" styleId="sortMetric" styleClass="form-control">
													<c:forEach var="item" items="${sortMetricItems}">
														<la:option value="${f:u(item)}">${f:h(item)}</la:option>
													</c:forEach>
												</la:select>
											</div>
										</div>
									</div>
								</div>
								<div class="box-footer">
									<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<a class="btn btn-info" role="button" data-toggle="collapse" href="#advanceSettings" aria-expanded="false"
										aria-controls="collapseExample"
									> <i class="far fa-plus-square"></i> Advance
									</a>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="runautoml" value="Run">
											<em class="fas fa-hammer"></em> Run
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
