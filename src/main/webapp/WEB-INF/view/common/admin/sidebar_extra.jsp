<%@page pageEncoding="UTF-8" contentType="text/html; charset=UTF-8"%>
<li class="nav-item has-treeview <c:if test="${param.menuCategoryType=='fione'}">menu-open</c:if>">
	<a href="#" class="nav-link <c:if test="${param.menuCategoryType=='fione'}">active</c:if>">
		<em class='nav-icon fas fa-robot'></em>
		<p>
			<la:message key="labels.menu_fione" />
			<i class="right fas fa-angle-left"></i>
		</p>
	</a>
	<ul class="nav nav-treeview">
		<li class="nav-item">
				<a href="${fe:url('/admin/easyml/')}" class="nav-link <c:if test="${param.menuType=='easyml'}">active</c:if>">
					<em class='fa fa-genderless nav-icon'></em>
					<p><la:message key="labels.menu_easyml" /></p>
				</a>
		</li>
		<li class="nav-item">
				<a href="${fe:url('/admin/automl/')}" class="nav-link <c:if test="${param.menuType=='automl'}">active</c:if>">
					<em class='fa fa-genderless nav-icon'></em>
					<p><la:message key="labels.menu_automl" /></p>
				</a>
		</li>
	</ul>
</li>
