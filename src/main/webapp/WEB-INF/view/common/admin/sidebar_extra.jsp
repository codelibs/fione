<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%>
<li class="treeview <c:if test="${param.menuCategoryType=='fione'}">active</c:if>"><a href="#"><i
		class='fa fa-wrench'
	></i> <span><la:message key="labels.menu_fione" /></span> <i class="fa fa-angle-left pull-right"></i></a>
	<ul class="treeview-menu">
		<li <c:if test="${param.menuType=='automl'}">class="active"</c:if>><la:link href="/admin/automl/">
				<i class='fa fa-circle-o'></i>
				<span><la:message key="labels.menu_automl" /></span>
			</la:link></li>
	</ul></li>

