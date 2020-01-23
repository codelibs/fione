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
				<h1><la:message key="labels.automl_run_automl" /></h1>
				<ol class="breadcrumb">
					<li><la:link href="/admin/automl">
							<la:message key="labels.crud_link_list" />
						</la:link></li>
					<li><la:link href="/admin/automl/details/${f:u(projectId)}">
							<la:message key="labels.automl_project" />
						</la:link></li>
					<li class="active"><la:message key="labels.automl_run_automl" /></li>
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
									<h3 class="box-title"><la:message key="labels.automl_settings" /></h3>
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
									<h4><la:message key="labels.automl_basic" /></h4>
									<div class="form-group">
										<label for="responseColumn" class="col-sm-3 control-label"><la:message key="labels.automl_predicted_column" /></label>
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
										<label for="maxRuntimeSecs" class="col-sm-3 control-label"><la:message key="labels.automl_max_runtime_secs" /></label>
										<div class="col-sm-9">
											<la:errors property="maxRuntimeSecs" />
											<input type="number" name="maxRuntimeSecs" id="maxRuntimeSecs" value="${f:h(maxRuntimeSecs)}"
												class="form-control" min="0"
											>
										</div>
									</div>
									<h4><la:message key="labels.automl_advance" />
									<a class="btn btn-link" role="button" data-toggle="collapse" href="#advanceSettings" aria-expanded="false"
										aria-controls="collapseSettings"
									><i class="fas fa-caret-down"></i></a></h4>
									<div class="collapse" id="advanceSettings">
										<div class="form-group">
											<label for="projectName" class="col-sm-3 control-label"><la:message key="labels.automl_project_name" /></label>
											<div class="col-sm-9">
												<la:errors property="projectName" />
												<la:text property="projectName" styleClass="form-control"/>
											</div>
										</div>
										<div class="form-group">
											<label class="col-sm-3 control-label"><la:message key="labels.automl_ignored_columns" /></label>
											<div class="col-sm-9 checkbox">
											<c:forEach var="item" varStatus="s" items="${columnItems}">
												<label><input type="checkbox" name="ignoredColumns.${f:h(item)}">${f:h(item)}</label>
											</c:forEach>
											</div>
										</div>
										<div class="form-group">
											<label for="nfolds" class="col-sm-3 control-label"><la:message key="labels.automl_nfolds" /></label>
											<div class="col-sm-9">
												<la:errors property="nfolds" />
												<input type="number" name="nfolds" id="nfolds" value="${f:h(nfolds)}" class="form-control" min="0">
											</div>
										</div>
										<div class="form-group">
											<label for="balanceClasses" class="col-sm-3 control-label"><la:message key="labels.automl_balance_classes" /></label>
											<div class="col-sm-9">
												<la:errors property="balanceClasses" />
												<la:select property="balanceClasses" styleId="balanceClasses" styleClass="form-control">
													<la:option value="true"><la:message key="labels.automl_true" /></la:option>
													<la:option value="false"><la:message key="labels.automl_false" /></la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="seed" class="col-sm-3 control-label"><la:message key="labels.automl_seed" /></label>
											<div class="col-sm-9">
												<la:errors property="seed" />
												<input type="number" name="seed" id="seed" value="${f:h(seed)}" class="form-control">
											</div>
										</div>
										<div class="form-group">
											<label for="maxModels" class="col-sm-3 control-label"><la:message key="labels.automl_max_models" /></label>
											<div class="col-sm-9">
												<la:errors property="seed" />
												<input type="number" name="maxModels" id="maxModels" value="${f:h(maxModels)}" class="form-control" min="0">
											</div>
										</div>
										<div class="form-group">
											<label for="maxRuntimeSecsPerModel" class="col-sm-3 control-label"><la:message key="labels.automl_max_runtime_secs_per_model" /></label>
											<div class="col-sm-9">
												<la:errors property="maxRuntimeSecsPerModel" />
												<input type="number" name="maxRuntimeSecsPerModel" id="maxRuntimeSecsPerModel"
													value="${f:h(maxRuntimeSecsPerModel)}" class="form-control" min="0"
												>
											</div>
										</div>
										<div class="form-group">
											<label for="stoppingRounds" class="col-sm-3 control-label"><la:message key="labels.automl_stopping_rounds" /></label>
											<div class="col-sm-9">
												<la:errors property="stoppingRounds" />
												<input type="number" name="stoppingRounds" id="stoppingRounds" value="${f:h(stoppingRounds)}"
													class="form-control" min="0"
												>
											</div>
										</div>
										<div class="form-group">
											<label for="stoppingMetric" class="col-sm-3 control-label"><la:message key="labels.automl_stopping_metric" /></label>
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
											<label for="stoppingTolerance" class="col-sm-3 control-label"><la:message key="labels.automl_stopping_tolerance" /></label>
											<div class="col-sm-9">
												<la:errors property="stoppingTolerance" />
												<la:text styleId="stoppingTolerance" property="stoppingTolerance" styleClass="form-control" />
											</div>
										</div>
										<div class="form-group">
											<label for="keepCrossValidationPredictions" class="col-sm-3 control-label"><la:message key="labels.automl_keep_xval_redictions" /></label>
											<div class="col-sm-9">
												<la:errors property="keepCrossValidationPredictions" />
												<la:select property="keepCrossValidationPredictions" styleId="keepCrossValidationPredictions"
													styleClass="form-control"
												>
													<la:option value="true"><la:message key="labels.automl_true" /></la:option>
													<la:option value="false"><la:message key="labels.automl_false" /></la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="keepCrossValidationModels" class="col-sm-3 control-label"><la:message key="labels.automl_keep_xval_models" /></label>
											<div class="col-sm-9">
												<la:errors property="keepCrossValidationModels" />
												<la:select property="keepCrossValidationModels" styleId="keepCrossValidationModels"
													styleClass="form-control"
												>
													<la:option value="true"><la:message key="labels.automl_true" /></la:option>
													<la:option value="false"><la:message key="labels.automl_false" /></la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="keepCrossValidationFoldAssignment" class="col-sm-3 control-label"><la:message key="labels.automl_keep_xval_fold_assignment" /></label>
											<div class="col-sm-9">
												<la:errors property="keepCrossValidationFoldAssignment" />
												<la:select property="keepCrossValidationFoldAssignment" styleId="keepCrossValidationFoldAssignment"
													styleClass="form-control"
												>
													<la:option value="true"><la:message key="labels.automl_true" /></la:option>
													<la:option value="false"><la:message key="labels.automl_false" /></la:option>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="sortMetric" class="col-sm-3 control-label"><la:message key="labels.automl_sort_metric" /></label>
											<div class="col-sm-9">
												<la:errors property="sortMetric" />
												<la:select property="sortMetric" styleId="sortMetric" styleClass="form-control">
													<c:forEach var="item" items="${sortMetricItems}">
														<la:option value="${f:u(item)}">${f:h(item)}</la:option>
													</c:forEach>
												</la:select>
											</div>
										</div>
										<div class="form-group">
											<label for="maxCategoricalFeatures" class="col-sm-3 control-label"><la:message key="labels.automl_max_categorical_features" /></label>
											<div class="col-sm-9">
												<la:errors property="maxCategoricalFeatures" />
												<input type="number" name="maxCategoricalFeatures" id="maxCategoricalFeatures"
													value="${f:h(maxCategoricalFeatures)}" class="form-control" min="0"
												>
											</div>
										</div>
									</div>
								</div>
								<div class="box-footer">
									<la:link href="/admin/automl/details/${f:u(projectId)}" styleClass="btn btn-default">
										<em class="fa fa-arrow-circle-left"></em>
										<la:message key="labels.crud_button_back" />
									</la:link>
									<c:if test="${editable}">
										<button type="submit" class="btn btn-success" name="runautoml" value="Run">
											<em class="fas fa-hammer"></em> <la:message key="labels.automl_run" />
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
