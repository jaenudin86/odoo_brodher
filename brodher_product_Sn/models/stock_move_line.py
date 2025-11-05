# -*- coding: utf-8 -*-
from odoo import models, fields, api, _

class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'
    
    serial_number_id = fields.Many2one(
        'product.serial.number',
        string='Serial Number',
        domain="[('product_tmpl_id', '=', product_id)]"
    )
    
    @api.onchange('serial_number_id')
    def _onchange_serial_number_id(self):
        """Auto fill lot name from serial number"""
        if self.serial_number_id:
            self.lot_name = self.serial_number_id.name