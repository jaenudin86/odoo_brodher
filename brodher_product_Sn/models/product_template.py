# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class ProductTemplate(models.Model):
    _inherit = 'product.template'
    
    sn_product_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='SN Product Type', default='M', required=True)
    
    serial_number_ids = fields.One2many(
        'product.serial.number', 
        'product_tmpl_id', 
        string='Serial Numbers'
    )
    
    serial_count = fields.Integer(
        string='Total Serial Numbers',
        compute='_compute_serial_count'
    )
    
    @api.depends('serial_number_ids')
    def _compute_serial_count(self):
        for record in self:
            record.serial_count = len(record.serial_number_ids)
    
    def action_generate_serial_numbers(self):
        """Open wizard untuk generate serial numbers"""
        self.ensure_one()
        return {
            'name': _('Generate Serial Numbers'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_product_tmpl_id': self.id,
                'default_sn_type': self.sn_product_type,
            }
        }
    
    def action_view_serial_numbers(self):
        """View all serial numbers for this product"""
        self.ensure_one()
        return {
            'name': _('Serial Numbers'),
            'type': 'ir.actions.act_window',
            'res_model': 'product.serial.number',
            'view_mode': 'tree,form',
            'domain': [('product_tmpl_id', '=', self.id)],
            'context': {'default_product_tmpl_id': self.id}
        }