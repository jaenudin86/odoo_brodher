# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class SNValidationWizard(models.TransientModel):
    _name = 'sn.validation.wizard'
    _description = 'SN Validation Warning'
    
    picking_id = fields.Many2one('stock.picking', string='Picking', required=True)
    warning_message = fields.Text(string='Warning', readonly=True)
    
    def action_continue_scan(self):
        """Return to scan wizard"""
        return self.picking_id.action_scan_serial_number()
    
    def action_force_validate(self):
        """Force validate without complete SN scan"""
        return self.picking_id.action_force_validate()