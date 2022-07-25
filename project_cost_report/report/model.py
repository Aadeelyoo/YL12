#-*- coding:utf-8 -*-

from odoo import api, models, fields
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta

class ProjectCostReports(models.AbstractModel):
	_name = 'report.project_cost_report.project_cost_temp_id'
	_description = 'Project Cost Reports'

	@api.model
	def _get_report_values(self, docids, data=None):
		docs = self.env['analytic.wbs.record'].browse(docids)

		date = fields.Date.today()
		project_name = docs.name
		project_id_name = docs.project_id.name

		project_wbs = []
		data_type = []
		data_type_past = []
		for pro in docs.record_line_ids:
			if pro.project_wbs_id:
				if pro.project_wbs_id not in project_wbs:
					project_wbs.append(pro.project_wbs_id)
			if pro.data_col:
				if pro.data_col not in data_type and pro.data_col_group == '60-Forecast':
					data_type.append(pro.data_col)
				if pro.data_col not in data_type_past and pro.data_col_group == '42-Past Incurred':
					data_type_past.append(pro.data_col)


		data_type_nine = []
		data_type = sorted(data_type)
		for nine in data_type:
			if len(data_type_nine) <= 9:
				data_type_nine.append(nine)

		data_type_two = []
		data_type_past = sorted(data_type_past, reverse=True)
		for two in data_type_past:
			if len(data_type_two) <= 1:
				data_type_two.append(two)

		fst_past_month = ""
		snd_past_month = ""
		if len(data_type_two) > 0:
			if len(data_type_two) > 1:
				fst_past_month = data_type_two[1]
			snd_past_month = data_type_two[0]


		project_wbs = sorted(project_wbs, key=lambda k: k.name)
	

		main_data = []
		summing_month_tot = []
		summing_tot_dynamic = []
		var_comm_tot = 0
		tot_comm_tot = 0
		act_comm_tot = 0
		open_comm_tot = 0
		eac_past_tot = 0
		eac_var_tot = 0
		eac_tot_tot = 0
		etc_past_tot = 0
		etc_var_tot = 0
		etc_tot_tot = 0
		etc_count_tot = 0
		incured_past_tot = 0
		incured_var_tot = 0
		incured_tot_tot = 0
		accurals_tot_tot = 0
		working_tot_tot = 0
		allocated_tot_tot = 0
		crout_tot_tot = 0
		po_crout_tot = 0
		po_cr_tot = 0
		po_eac_tot = 0
		fst_month_tot = 0
		snd_month_tot = 0
		
		for rec in project_wbs:
			rep_data_type = []
			rep_rec = []
			rep_records = self.env['analytic.wbs.record.line'].search([('project_wbs_id','=',rec.id),('record_id','=',docs.id)])
			if rep_records:
				for rep in rep_records:
					if rep.rep_uid_type:
						if rep.rep_uid_type not in rep_data_type:
							rep_data_type.append(rep.rep_uid_type)

			summing_month_wbs = []
			summing_wbs_dynamic = []
			var_comm_wbs = 0
			tot_comm_wbs = 0
			act_comm_wbs = 0
			open_comm_wbs = 0
			eac_past_wbs = 0
			eac_var_wbs = 0
			eac_tot_wbs = 0
			etc_past_wbs = 0
			etc_var_wbs = 0
			etc_tot_wbs = 0
			etc_count_wbs = 0
			incured_past_wbs = 0
			incured_var_wbs = 0
			incured_tot_wbs = 0
			accurals_tot_wbs = 0
			crout_tot_wbs = 0
			po_crout_wbs = 0
			po_cr_wbs = 0
			po_eac_wbs = 0
			fst_month_wbs = 0
			snd_month_wbs = 0
			working_tot_wbs = 0
			allocated_tot_wbs = 0
			budget_total = 0
			allocated_total = 0
			working_total = 0
			working_bdgt_total = 0
			cont_trend_total = 0
			scope_total = 0
			transfer_total = 0

			if rep_data_type:
				rep_data_type = sorted(rep_data_type)
				for data in rep_data_type:
					line_data = []
					rep_name_rec = []
					line_records = self.env['analytic.wbs.record.line'].search([('project_wbs_id','=',rec.id),('rep_uid_type','=',data),('record_id','=',docs.id)])
					if line_records:
						for line in line_records:
							if line.rep_uid not in rep_name_rec:
								rep_name_rec.append(line.rep_uid)

						var_comm_name = 0
						tot_comm_name = 0
						act_comm_name = 0
						open_comm_name = 0
						eac_past_name = 0
						eac_var_name = 0
						eac_tot_name = 0
						etc_past_name = 0
						etc_var_name = 0
						etc_tot_name = 0
						etc_count_name = 0
						incured_past_name = 0
						incured_var_name = 0
						incured_tot_name = 0
						accurals_tot_name = 0
						crout_tot_name = 0
						po_crout_name = 0 
						po_cr_name = 0 
						po_eac_name = 0
						fst_month_name = 0
						snd_month_name = 0
						working_tot_name = 0
						allocated_tot_name = 0
						summing_month_name = []
						summing_month_dynamic = []
						for final in rep_name_rec:
							summing_month = []
							final_records = self.env['analytic.wbs.record.line'].search([('project_wbs_id','=',rec.id),('rep_uid_type','=',data),('rep_uid','=',final),('record_id','=',docs.id)])
							if final_records:
								var_comm = 0
								tot_comm = 0
								act_comm = 0
								open_comm = 0
								eac_past = 0
								eac_var = 0
								eac_tot = 0
								etc_past = 0
								etc_var = 0
								etc_tot = 0
								etc_count = 0
								incured_past = 0
								incured_var = 0
								incured_tot = 0
								accurals_tot = 0
								crout_tot = 0
								po_crout = 0
								po_cr = 0
								po_eac = 0
								fst_month = 0
								snd_month = 0
								working_tot = 0
								allocated_tot = 0
								partner_name = ""
								descp = ""
								line_total = 0
								data_type_rec = []
								for result in final_records:
									month_value = []
									for months in data_type_nine:
										if months == result.data_col and result.data_col_group == '60-Forecast':
											month_value.append(result.amount)
											line_total = line_total + result.amount
										else:
											month_value.append(0)

									data_type_rec.append(month_value)

									if result.data_col == 'Open Commitments':
										open_comm = open_comm + result.amount
									if result.data_col == 'Total':
										tot_comm = tot_comm + result.amount
										var_comm = var_comm + result.variance
									if result.data_col == 'Actuals':
										act_comm = act_comm + result.amount

									if result.data_col == 'EAC':
										eac_past = eac_past + result.past_amount
										eac_var = eac_var + result.variance
										eac_tot = eac_tot + result.amount

									if result.data_col_group == '40-Incurred Total':
										incured_past = incured_past + result.past_amount
										incured_tot = incured_tot + result.amount

									if result.data_col_group == '50-Incurred Current':
										incured_var = incured_var + result.amount

									if result.data_col == 'ETC':
										etc_past = etc_past + result.past_amount
										etc_var = etc_var + result.variance
										etc_tot = etc_tot + result.amount

									if result.data_col == 'ETC Contingency':
										etc_count = etc_count + result.amount

									if 'Employee' in result.rep_uid_type and result.employee_id:partner_name = result.employee_id.name
									if 'Purchase' in result.rep_uid_type and result.partner_id:partner_name = result.partner_id.name

									if result.data_col == 'Budget':
										budget_total = budget_total + result.amount

									if result.data_col == 'Invoices' or result.data_col == 'LEMs' or result.data_col == 'Others':
										accurals_tot = accurals_tot + result.amount

									if result.data_col == 'Outstanding CR':
										crout_tot = crout_tot + result.amount

									if result.data_col == 'Bdgt. Work':
										working_tot = working_tot + result.amount
										working_total = working_total + result.amount

									if result.data_col == 'Bdgt. Work No Ctgcy':
										working_bdgt_total = working_bdgt_total + result.amount

									if result.data_col == 'Contingency Allocation':
										allocated_tot = allocated_tot + result.amount
										allocated_total = allocated_total + result.amount

									if result.data_col == 'Cont. Trend Change':
										cont_trend_total = cont_trend_total + result.amount

									if result.data_col == 'Scope Change':
										scope_total = scope_total + result.amount

									if result.data_col == 'Transfer':
										transfer_total = transfer_total + result.amount

									if result.data_col == fst_past_month:
										fst_month = fst_month + result.amount

									if result.data_col == snd_past_month:
										snd_month = snd_month + result.amount

									po_crout = tot_comm + crout_tot
									po_cr = eac_tot - po_crout
									po_eac = eac_tot - working_tot

									if result.task_id:
										descp = result.task_id.name

							summing_month = [sum(x) for x in zip(*data_type_rec)]
							summing_month_dynamic.append(summing_month)

							var_comm_name = var_comm_name + var_comm
							tot_comm_name = tot_comm_name + tot_comm
							act_comm_name = act_comm_name + act_comm
							open_comm_name = open_comm_name + open_comm
							eac_past_name = eac_past_name + eac_past 
							eac_var_name = eac_var_name + eac_var
							eac_tot_name = eac_tot_name + eac_tot
							etc_past_name = etc_past_name + etc_past
							etc_var_name = etc_var_name + etc_var
							etc_tot_name = etc_tot_name + etc_tot
							etc_count_name = etc_count_name + etc_count
							incured_past_name = incured_past_name + incured_past
							incured_var_name = incured_var_name + incured_var
							incured_tot_name = incured_tot_name + incured_tot
							accurals_tot_name = accurals_tot_name + accurals_tot
							crout_tot_name = crout_tot_name + crout_tot
							po_crout_name = po_crout_name + po_crout
							po_cr_name = po_cr_name + po_cr
							po_eac_name = po_eac_name + po_eac
							fst_month_name = fst_month_name + fst_month
							snd_month_name = snd_month_name + snd_month
							working_tot_name = working_tot_name + working_tot
							allocated_tot_name = allocated_tot_name + allocated_tot


							if var_comm != 0 or tot_comm != 0 or act_comm != 0 or open_comm != 0 or po_crout != 0 or po_cr != 0 or po_eac != 0 or fst_month != 0 or snd_month != 0 or eac_past != 0 or eac_var != 0 or eac_tot != 0 or etc_past != 0 or etc_var != 0 or etc_tot != 0 or etc_count != 0 or incured_past != 0 or incured_var != 0 or incured_tot != 0 or accurals_tot != 0 or crout_tot != 0 :

								line_data.append({
									'rep_name':result.rep_name,
									'vendor':partner_name,
									'project_id':result.project_id,
									'project_wbs_id':result.project_wbs_id.id,
									'employee_id':result.employee_id.id,
									'partner_id':result.partner_id,
									'po_id':result.po_id.id,
									'task_id':result.task_id.id,
									'rep_uid_type':result.rep_uid_type,
									'descp':descp,
									'working_tot':working_tot,
									'allocated_tot':allocated_tot,
									'var_comm':var_comm,
									'tot_comm':tot_comm,
									'act_comm':act_comm,
									'open_comm':open_comm,
									'po_crout':po_crout,
									'po_cr':po_cr,
									'po_eac':po_eac,
									'fst_month':fst_month,
									'snd_month':snd_month,
									'eac_past':eac_past,
									'eac_var':eac_var,
									'eac_tot':eac_tot,
									'etc_past':etc_past,
									'etc_var':etc_var,
									'etc_tot':etc_tot,
									'etc_count':etc_count,
									'incured_past':incured_past,
									'incured_var':incured_var,
									'incured_tot':incured_tot,
									'accurals_tot':accurals_tot,
									'crout_tot':crout_tot,
									'data_type_rec':summing_month,
									'line_total':line_total,
									})


						summing_month_name = [sum(x) for x in zip(*summing_month_dynamic)]
						summing_wbs_dynamic.append(summing_month_name)

						var_comm_wbs = var_comm_wbs + var_comm_name
						tot_comm_wbs = tot_comm_wbs + tot_comm_name
						act_comm_wbs = act_comm_wbs + act_comm_name
						open_comm_wbs = open_comm_wbs + open_comm_name
						eac_past_wbs = eac_past_wbs + eac_past_name 
						eac_var_wbs = eac_var_wbs + eac_var_name
						eac_tot_wbs = eac_tot_wbs + eac_tot_name
						etc_past_wbs = etc_past_wbs + etc_past_name
						etc_var_wbs = etc_var_wbs + etc_var_name
						etc_tot_wbs = etc_tot_wbs + etc_tot_name
						etc_count_wbs = etc_count_wbs + etc_count_name
						incured_past_wbs = incured_past_wbs + incured_past_name
						incured_var_wbs = incured_var_wbs + incured_var_name
						incured_tot_wbs = incured_tot_wbs + incured_tot_name
						accurals_tot_wbs = accurals_tot_wbs + accurals_tot_name
						crout_tot_wbs = crout_tot_wbs + crout_tot_name
						po_crout_wbs = po_crout_wbs + po_crout_name
						po_cr_wbs = po_cr_wbs + po_cr_name
						po_eac_wbs = po_eac_wbs + po_eac_name
						fst_month_wbs = fst_month_wbs + fst_month_name
						snd_month_wbs = snd_month_wbs + snd_month_name
						working_tot_wbs = working_tot_wbs + working_tot_name
						allocated_tot_wbs = allocated_tot_wbs + allocated_tot_name

						if len(line_data) > 0:
							rep_rec.append({
								'line_data':line_data,
								'rep_name':data,
								'var_comm_name':var_comm_name,
								'tot_comm_name':tot_comm_name,
								'act_comm_name':act_comm_name,
								'open_comm_name':open_comm_name,
								'eac_past_name':eac_past_name,
								'eac_var_name':eac_var_name,
								'eac_tot_name':eac_tot_name,
								'etc_past_name':etc_past_name,
								'etc_var_name':etc_var_name,
								'etc_tot_name':etc_tot_name,
								'etc_count_name':etc_count_name,
								'incured_past_name':incured_past_name,
								'incured_var_name':incured_var_name,
								'incured_tot_name':incured_tot_name,
								'accurals_tot_name':accurals_tot_name,
								'working_tot_name':working_tot_name,
								'allocated_tot_name':allocated_tot_name,
								'crout_tot_name':crout_tot_name,
								'po_crout_name':po_crout_name,
								'po_cr_name':po_cr_name,
								'po_eac_name':po_eac_name,
								'fst_month_name':fst_month_name,
								'snd_month_name':snd_month_name,
								'summing_month_name':summing_month_name,
								})


				summing_month_wbs = [sum(x) for x in zip(*summing_wbs_dynamic)]
				summing_tot_dynamic.append(summing_month_wbs)

				var_comm_tot = var_comm_tot + var_comm_wbs
				tot_comm_tot = tot_comm_tot + tot_comm_wbs
				act_comm_tot = act_comm_tot + act_comm_wbs
				open_comm_tot = open_comm_tot + open_comm_wbs
				eac_past_tot = eac_past_tot + eac_past_wbs 
				eac_var_tot = eac_var_tot + eac_var_wbs
				eac_tot_tot = eac_tot_tot + eac_tot_wbs
				etc_past_tot = etc_past_tot + etc_past_wbs
				etc_var_tot = etc_var_tot + etc_var_wbs
				etc_tot_tot = etc_tot_tot + etc_tot_wbs
				etc_count_tot = etc_count_tot + etc_count_wbs
				incured_past_tot = incured_past_tot + incured_past_wbs
				incured_var_tot = incured_var_tot + incured_var_wbs
				incured_tot_tot = incured_tot_tot + incured_tot_wbs
				accurals_tot_tot = accurals_tot_tot + accurals_tot_wbs
				crout_tot_tot = crout_tot_tot + crout_tot_wbs
				po_crout_tot = po_crout_tot + po_crout_wbs
				po_cr_tot = po_cr_tot + po_cr_wbs
				po_eac_tot = po_eac_tot + po_eac_wbs
				fst_month_tot = fst_month_tot + fst_month_wbs
				snd_month_tot = snd_month_tot + snd_month_wbs
				working_tot_tot = working_tot_tot + working_tot_wbs
				allocated_tot_tot = allocated_tot_tot + allocated_tot_wbs

				if len(rep_rec) > 0:
					main_data.append({
						'rep_rec':rep_rec,
						'project_wbs':rec.name,
						'project_wbs_id':rec.id,
						'descr_short':rec.descr_short,
						'budget_total':budget_total,
						'allocated_total':allocated_total,
						'working_total':working_total,
						'working_bdgt_total':working_bdgt_total,
						'cont_trend_total':cont_trend_total,
						'scope_total':scope_total,
						'transfer_total':transfer_total,
						'var_comm_wbs':var_comm_wbs,
						'tot_comm_wbs':tot_comm_wbs,
						'act_comm_wbs':act_comm_wbs,
						'open_comm_wbs':open_comm_wbs,
						'eac_past_wbs':eac_past_wbs,
						'eac_var_wbs':eac_var_wbs,
						'eac_tot_wbs':eac_tot_wbs,
						'etc_past_wbs':etc_past_wbs,
						'etc_var_wbs':etc_var_wbs,
						'etc_tot_wbs':etc_tot_wbs,
						'etc_count_wbs':etc_count_wbs,
						'incured_past_wbs':incured_past_wbs,
						'incured_var_wbs':incured_var_wbs,
						'incured_tot_wbs':incured_tot_wbs,
						'accurals_tot_wbs':accurals_tot_wbs,
						'crout_tot_wbs':crout_tot_wbs,
						'po_crout_wbs':po_crout_wbs,
						'po_cr_wbs':po_cr_wbs,
						'po_eac_wbs':po_eac_wbs,
						'fst_month_wbs':fst_month_wbs,
						'snd_month_wbs':snd_month_wbs,
						'working_tot_wbs':working_tot_wbs,
						'allocated_tot_wbs':allocated_tot_wbs,
						'summing_month_wbs':summing_month_wbs,
						})


		summing_month_tot = [sum(x) for x in zip(*summing_tot_dynamic)]

		def get_po_url(attr):

			return "/po?internalref="+str(attr)

		def get_emp_url(attr):

			return "/employee?id="+str(attr)

		def get_wbs_url(attr):

			return "/projectwbs?id="+str(attr)

		def get_emp_wbs_url(attr,attr1):

			return "/forecast?employee_id="+str(attr)+"&project_wbs_id="+str(attr1)

		def get_task_wbs_url(attr,attr1):

			return "/forecast?task_id="+str(attr)+"&project_wbs_id="+str(attr1)

		def get_po_wbs_url(attr,attr1):

			return "/forecast?po_id="+str(attr)+"&project_wbs_id="+str(attr1)

		def get_tot_wbs_url(attr):

			return "/forecast?task_id=all&employee_id=none&po_id=none&project_wbs_id="+str(attr)

		def get_total_wbs_url(attr):

			return "/forecast?task_id=all&project_wbs_id="+str(attr)

		return {
			'doc_ids': docids,
			'date': date,
			'project_name': project_name,
			'main_data': main_data,
			'data_type': data_type_nine,
			'col_size': len(data_type_nine),
			'var_comm_tot': var_comm_tot,
			'tot_comm_tot': tot_comm_tot,
			'act_comm_tot': act_comm_tot,
			'open_comm_tot': open_comm_tot,
			'eac_past_tot': eac_past_tot,
			'eac_var_tot': eac_var_tot,
			'eac_tot_tot': eac_tot_tot,
			'etc_past_tot': etc_past_tot,
			'etc_var_tot': etc_var_tot,
			'etc_tot_tot': etc_tot_tot,
			'etc_count_tot': etc_count_tot,
			'incured_past_tot': incured_past_tot,
			'incured_var_tot': incured_var_tot,
			'incured_tot_tot': incured_tot_tot,
			'accurals_tot_tot': accurals_tot_tot,
			'crout_tot_tot': crout_tot_tot,
			'po_crout_tot': po_crout_tot,
			'po_cr_tot': po_cr_tot,
			'po_eac_tot': po_eac_tot,
			'working_tot_tot': working_tot_tot,
			'allocated_tot_tot': allocated_tot_tot,
			'summing_month_tot': summing_month_tot,
			'fst_past_month': fst_past_month,
			'snd_past_month': snd_past_month,
			'fst_month_tot': fst_month_tot,
			'snd_month_tot': snd_month_tot,
			'get_po_url': get_po_url,
			'get_emp_url': get_emp_url,
			'project_id_name': project_id_name,
			'get_wbs_url': get_wbs_url,
			'get_emp_wbs_url': get_emp_wbs_url,
			'get_po_wbs_url': get_po_wbs_url,
			'get_task_wbs_url': get_task_wbs_url,
			'get_tot_wbs_url': get_tot_wbs_url,
			'get_total_wbs_url': get_total_wbs_url,

		}

