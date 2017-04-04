# -*- coding: utf-8 -*-

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

class res_company(models.Model):
	_inherit = 'res.company'

	@api.constrains('default_purchase_tax_id')
	def _check_purchase_tax(self):
		if self.default_purchase_tax_id:
			if self.id != self.default_purchase_tax_id.company_id.id:
				raise ValidationError("Impuesto seleccionado no corresponde a la empresa")

	@api.constrains('default_sale_tax_id')
	def _check_purchase_tax(self):
		if self.default_sale_tax_id:
			if self.id != self.default_sale_tax_id.company_id.id:
				raise ValidationError("Impuesto seleccionado no corresponde a la empresa")
		
	
	default_purchase_tax_id = fields.Many2one('account.tax',string='Impuesto Default en Compras')
	default_sale_tax_id = fields.Many2one('account.tax',string='Impuesto Default en Ventas')

class product_taxes(models.Model):
        _name = 'product.taxes'
	_description = 'Impuestos del producto'

	@api.constrains('product_id','company_id','tax_id')
	def _check_tax_unique(self):
		cnt = self.env['product.taxes'].search([('company_id','=',self.company_id.id),\
			('tax_id','=',self.tax_id.id),('product_id','=',self.product_id.id)])
		if cnt and len(cnt) > 1:
			raise ValidationError('Solo se debe tener un impuesto por producto por empresa')

	@api.one
	def _compute_name(self):
		return_value = ''
		if self.company_id and self.tax_id:
			return_value = self.company_id.name + ' - ' + self.tax_id.name
		self.name = return_value
        
	name = fields.Char('Name',compute=_compute_name)
	product_id = fields.Many2one('product.product',string='Product')
	company_id = fields.Many2one('res.company',string='Company')
	tax_id = fields.Many2one('account.tax',string='Tax')
	sale_tax_id = fields.Many2one('account.tax',string='Sale Tax')

class account_tax(models.Model):
	_inherit = 'account.tax'

	company_taxes = fields.One2many(comodel_name='account.tax.equivalent',inverse_name='tax_id')

class account_tax_equivalent(models.Model):
	_name = 'account.tax.equivalent'
	_description = 'account.tax.equivalent'

	@api.one
	def _compute_name(self):
		return_value = ''
		if self.company_id and self.equivalent_tax_id:
			return_value = self.company_id.name + ' - ' + self.equivalent_tax_id.name
		self.name = return_value

	@api.one
	@api.constrains('company_id','equivalent_tax_id')
	def constrains_equivalent(self):
		if self.company_id and self.equivalent_tax_id:
			if self.company_id.id != self.equivalent_tax_id.company_id.id:
				raise ValidationError('Se seleccionó un impuesto que no corresponde\na la compañía  en la que se está trabajando')

	name = fields.Char('Nombre impuesto',compute=_compute_name)
	company_id = fields.Many2one('res.company',string='Company',required=True)
	tax_id = fields.Many2one('account.tax',string='Tax')
	equivalent_tax_id = fields.Many2one('account.tax',string='Equivalent Tax',required=True)

class purchase_order_line(models.Model):
	_inherit = 'purchase.order.line'

	@api.model
	def create(self,vals):
		product_id = vals.get('product_id',False)
		order_id = vals.get('order_id',False)
		product = self.env['product.product'].browse(product_id)
		if product_id and order_id and product.supplier_taxes_id:
			order = self.env['purchase.order'].browse(order_id)
			product_tax = self.env['account.tax.equivalent'].search([('tax_id','=',product.supplier_taxes_id.ids[0]),\
					('company_id','=',order.company_id.id)])
			if product_tax:
				return_value = [[6,0,[product_tax.equivalent_tax_id.id]]]
				vals['taxes_id'] = return_value
			#if not product_tax:
			#	return_value = [[6,0,[order.company_id.default_purchase_tax_id.id]]]
			#	vals['taxes_id'] = return_value
                return super(purchase_order_line, self).create(vals)
	

class account_invoice_line(models.Model):
	_inherit = 'account.invoice.line'

	invoice_line_tax_ids = fields.Many2many('account.tax','account_invoice_line_tax', 'invoice_line_id', 'tax_id',\
	        string='Taxes', domain=[('type_tax_use','!=','none'), '|', ('active', '=', False), ('active', '=', True)],\
		 oldname='invoice_line_tax_id',readonly=True)


	@api.model
	def create(self,vals):
		product_id = vals.get('product_id',False)
		invoice_id = vals.get('invoice_id',False)
		product = self.env['product.product'].browse(product_id)
		if product_id and invoice_id and product.supplier_taxes_id:
			invoice = self.env['account.invoice'].browse(invoice_id)
			product_tax = self.env['account.tax.equivalent'].search([('tax_id','=',product.supplier_taxes_id.ids[0]),\
					('company_id','=',invoice.company_id.id)])
			if product_tax:
				return_value = [[6,0,[product_tax.equivalent_tax_id.id]]]
				vals['invoice_line_tax_ids'] = return_value	
                return super(account_invoice_line, self).create(vals)
		

class product_product(models.Model):
	_inherit = 'product.product'

	product_taxes_ids = fields.One2many(comodel_name='product.taxes',inverse_name='product_id')

        @api.model
        def create(self, vals):
                res = super(product_product, self).create(vals)
		companies = self.env['res.company'].search([])
		for company in companies:
			if company.default_purchase_tax_id:
				tax_values = {
					'product_id': res.id,
					'company_id': company.id,
					'tax_id': company.default_purchase_tax_id.id
					}
				return_id = self.env['product.taxes'].create(tax_values)
		return res
		
