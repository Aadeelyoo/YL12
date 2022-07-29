# -*- coding: utf-8 -*-

import imghdr
import json
import io
import base64
import functools
from odoo import http, tools
import odoo, os, sys, jinja2
from odoo.addons.web.controllers.main import Database
from odoo.addons.web.controllers import main
from odoo.tools.mimetypes import guess_mimetype
from odoo.addons.web.controllers.main import Binary
from odoo.modules import get_resource_path
from io import StringIO
from odoo.http import request

if hasattr(sys, 'frozen'):
    # When running on compiled windows binary, we don't have access to package loader.
    path = os.path.realpath(os.path.join(os.path.dirname(__file__), '..', 'views'))
    loader = jinja2.FileSystemLoader(path)
else:
    loader = jinja2.PackageLoader('odoo.addons.solevo-odoo-debrand', "views")
env = main.jinja2.Environment(loader=loader, autoescape=True)
env.filters["json"] = json.dumps
db_monodb = http.db_monodb
DBNAME_PATTERN = '^[a-zA-Z0-9][a-zA-Z0-9_.-]+$'


class BinaryCustom(Binary):
	@http.route([
	'/web/binary/company_logo',
	'/logo',
	'/logo.png',
	], type='http', auth="none")
	def company_logo(self, dbname=None, **kw):
		imgname = 'logo'
		imgext = '.png'
		placeholder = functools.partial(get_resource_path, 'web', 'static', 'src', 'img')
		uid = None
		if request.session.db:
			dbname = request.session.db
			uid = request.session.uid
		elif dbname is None:
			dbname = db_monodb()

		if not uid:
			uid = odoo.SUPERUSER_ID

		if not dbname:
			response = http.send_file(placeholder(imgname + imgext))
		else:
			try:
				# create an empty registry
				registry = odoo.modules.registry.Registry(dbname)
				with registry.cursor() as cr:
					company = int(kw['company']) if kw and kw.get('company') else False
					if company:
						cr.execute("""SELECT logo_web, write_date
	                                    FROM res_company
	                                   WHERE id = %s
	                               """, (company,))
					else:
						cr.execute("""SELECT c.logo_web, c.write_date
	                                    FROM res_users u
	                               LEFT JOIN res_company c
	                                      ON c.id = u.company_id
	                                   WHERE u.id = %s
	                               """, (uid,))
					row = cr.fetchone()
					if row and row[0]:
						image_base64 = base64.b64decode(row[0])
						image_data = io.BytesIO(image_base64)
						mimetype = guess_mimetype(image_base64, default='image/png')
						imgext = '.' + mimetype.split('/')[1]
						if imgext == '.svg+xml':
							imgext = '.svg'
						response = http.send_file(image_data, filename=imgname + imgext, mimetype=mimetype,
												  mtime=row[1])
					else:
						response = http.send_file(placeholder('nologo.png'))
			except Exception:
				response = http.send_file(placeholder(imgname + imgext))

		return response


class OdooDebrand(Database):
	def _render_template(self, **d):
		d.setdefault('manage', True)
		d['insecure'] = odoo.tools.config.verify_admin_password('admin')
		d['list_db'] = odoo.tools.config['list_db']
		d['langs'] = odoo.service.db.exp_list_lang()
		d['countries'] = odoo.service.db.exp_list_countries()
		d['pattern'] = DBNAME_PATTERN
		website_id = request.env['website'].sudo().search([])
		d['website_name'] = website_id and website_id[0].name or ''
		d['favicon']= website_id and	website_id[0].favicon_url or ''
		d['company_logo_url'] = website_id and website_id[0].company_logo_url or ''

		# databases list
		d['databases'] = []
		try:
				d['databases'] = http.db_list()
				d['incompatible_databases'] = odoo.service.db.list_db_incompatible(d['databases'])
		except odoo.exceptions.AccessDenied:
				monodb = db_monodb()
				if monodb:
						d['databases'] = [monodb]
		return env.get_template("database_manager_extend.html").render(d)
