from openerp import models, fields, api, _
from openerp.osv import osv
from openerp.exceptions import except_orm, ValidationError
from StringIO import StringIO
import urllib2, httplib, urlparse, gzip, requests, json
import openerp.addons.decimal_precision as dp
import logging
import datetime
from openerp.fields import Date as newdate

#Get the logger
_logger = logging.getLogger(__name__)

class purchase_order(models.Model):
	_inherit = 'purchase.order'

	@api.model
	def create(self, vals):
	        res = super(purchase_order, self).create(vals)
		purchase_state = res.state
		if purchase_state in ['draft','purchase','done']:
			order_line = vals.get('order_line',False)
			if order_line:
				for line in order_line:
					line = line[2]
					product_id = self.env['product.product'].browse(line['product_id'])
					pricelist_id = self.env['product.supplierinfo'].search([\
						('name','=',self.partner_id.id),\
						('product_tmpl_id','=',product_id.product_tmpl_id.id)])
					vals = {
						'name': res.partner_id.id,
						'product_tmpl_id': product_id.product_tmpl_id.id,
						'min_qty': 0,
						'price': line['price_unit']
						}
					if not pricelist_id:
						pricelist_id = self.env['product.supplierinfo'].create(vals)
					else:
						pricelist_id.write(vals)

		return res


	@api.multi
	def write(self, vals):
		purchase_state = vals.get('state','')
		res = super(purchase_order,self).write(vals)
		if purchase_state == '':
			purchase_state = self.state
		if purchase_state in ['draft','purchase','done']:
			for line in self.order_line:
				pricelist_id = self.env['product.supplierinfo'].search([\
					('name','=',self.partner_id.id),\
					('product_tmpl_id','=',line.product_id.product_tmpl_id.id)])
				vals = {
					'name': self.partner_id.id,
					'product_tmpl_id': line.product_id.product_tmpl_id.id,
					'min_qty': 0,
					'price': line.price_unit
					}
				if not pricelist_id:
					pricelist_id = self.env['product.supplierinfo'].create(vals)
				else:
					pricelist_id.write(vals)
				if purchase_state in ['purchase','done']:
					vals_product_tmpl = {
						'standard_price': line.price_unit
						}
					product_tmpl = line.product_id.product_tmpl_id
					product_tmpl.write(vals_product_tmpl)
		return res

class account_invoice(models.Model):
	_inherit = 'account.invoice'


	@api.multi
	def write(self, vals):
		invoice_state = vals.get('state','')
		res = super(account_invoice,self).write(vals)
		if invoice_state in ['open']:
			for line in self.invoice_line_ids:
				pricelist_id = self.env['product.supplierinfo'].search([\
					('name','=',self.partner_id.id),\
					('product_tmpl_id','=',line.product_id.product_tmpl_id.id)])
				vals = {
					'name': self.partner_id.id,
					'product_tmpl_id': line.product_id.product_tmpl_id.id,
					'min_qty': 0,
					'price': line.price_unit
					}
				if not pricelist_id:
					pricelist_id = self.env['product.supplierinfo'].create(vals)
				else:
					pricelist_id.write(vals)
				vals_product_tmpl = {
					'standard_price': line.price_unit
					}
				product_tmpl = line.product_id.product_tmpl_id
				product_tmpl.write(vals_product_tmpl)
		return res

class purchase_requisition(models.Model):
	_inherit = 'purchase.requisition'

	@api.multi
	def write(self,vals):
		requisition_state = vals.get('state','')
		res = super(purchase_requisition,self).write(vals)
		if requisition_state in ['done']:
			for purchase in self.purchase_ids:
				 if purchase.state == 'cancel':
					for line in purchase.order_line:
						pricelist_id = self.env['product.supplierinfo'].search([\
							('name','=',purchase.partner_id.id),\
							('product_tmpl_id','=',line.product_id.product_tmpl_id.id)])
						vals = {
							'name': purchase.partner_id.id,
							'product_tmpl_id': line.product_id.product_tmpl_id.id,
							'min_qty': 0,
							'price': line.price_unit
							}
						if not pricelist_id:
							pricelist_id = self.env['product.supplierinfo'].create(vals)
						else:
							pricelist_id.write(vals)
		return res
