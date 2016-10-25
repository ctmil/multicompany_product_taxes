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

class product_taxes(models.Model):
        _name = 'product.taxes'
	_description = 'Impuestos del producto'

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

class product_product(models.Model):
	_inherit = 'product.product'

	product_taxes_ids = fields.One2many(comodel_name='product.taxes',inverse_name='product_id')

        @api.model
        def create(self, vals):
                res = super(product_product, self).create(vals)
		companies = self.env['res.company'].search([])
		for company in companies:
			account_config_setting = self.env['account.config.setting'].search([('company_id','=',company.id)])
			if account_config_setting.default_purchase_tax_id:
				tax_values = {
					'company_id': company_id.id,
					'tax_id': account_config_setting.default_purchase_tax_id.id
					}
				return_id = self.env['product.taxes'].create(tax_values)
		return res
		
