# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    sn_move_ids = fields.One2many(
        'product.sn.move',
        'picking_id',
        string='Serial Number Moves'
    )
    
    sn_count = fields.Integer(
        string='SN Count',
        compute='_compute_sn_count'
    )
    
    scanned_sn_count = fields.Integer(
        string='Scanned SN',
        compute='_compute_scanned_sn_count'
    )
    
    require_sn_scan = fields.Boolean(
        string='Require SN Scan',
        compute='_compute_require_sn_scan',
        help='True if this picking contains products with serial numbers'
    )
    
    @api.depends('sn_move_ids')
    def _compute_sn_count(self):
        for picking in self:
            picking.sn_count = len(picking.sn_move_ids)
    
    @api.depends('sn_move_ids')
    def _compute_scanned_sn_count(self):
        for picking in self:
            picking.scanned_sn_count = len(picking.sn_move_ids)
    
    @api.depends('move_ids_without_package', 'move_ids_without_package.product_id')
    def _compute_require_sn_scan(self):
        for picking in self:
            # Check if any product in this picking has SN type
            has_sn_product = any(
                move.product_id.product_tmpl_id.sn_product_type
                for move in picking.move_ids_without_package
            )
            picking.require_sn_scan = has_sn_product
    
    def action_scan_serial_number(self):
        """Open wizard to scan serial number"""
        self.ensure_one()
        
        # Determine move type based on picking type
        move_type = 'internal'
        if self.picking_type_code == 'incoming':
            move_type = 'in'
        elif self.picking_type_code == 'outgoing':
            move_type = 'out'
        
        # Default locations
        location_src = self.location_id
        location_dest = self.location_dest_id
        
        # Get products that need scanning
        products_need_scan = self.move_ids_without_package.filtered(
            lambda m: m.product_id.product_tmpl_id.sn_product_type
        ).mapped('product_id')
        
        return {
            'name': _('Scan Serial Number - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'scan.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.id,
                'default_move_type': move_type,
                'default_location_src_id': location_src.id,
                'default_location_dest_id': location_dest.id,
                'allowed_product_ids': products_need_scan.ids,
            }
        }
    
    def action_view_sn_moves(self):
        """View SN moves"""
        self.ensure_one()
        return {
            'name': _('Serial Number Moves - %s') % self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'product.sn.move',
            'view_mode': 'tree,form',
            'domain': [('picking_id', '=', self.id)],
            'context': {'default_picking_id': self.id}
        }
    
    def _check_sn_scan_completion(self):
        """Check if all required SNs are scanned"""
        self.ensure_one()
        
        # Only check for pickings that require SN
        if not self.require_sn_scan:
            return True
        
        for move in self.move_ids_without_package:
            product_tmpl = move.product_id.product_tmpl_id
            
            # Skip products without SN requirement
            if not product_tmpl.sn_product_type:
                continue
            
            # Count scanned SNs for this product
            scanned_count = len(self.sn_move_ids.filtered(
                lambda sm: sm.serial_number_id.product_tmpl_id == product_tmpl
            ))
            
            required_qty = int(move.product_uom_qty)
            
            if scanned_count < required_qty:
                return False, _(
                    'Product "%s" requires %d serial numbers, but only %d scanned!'
                ) % (product_tmpl.name, required_qty, scanned_count)
        
        return True, None
    
    def button_validate(self):
        """Override validate to check scanned SNs"""
        for picking in self:
            if picking.require_sn_scan:
                is_complete, error_msg = picking._check_sn_scan_completion()
                
                if not is_complete:
                    # Show warning with option to continue
                    return {
                        'type': 'ir.actions.act_window',
                        'res_model': 'sn.validation.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_picking_id': picking.id,
                            'default_warning_message': error_msg,
                        }
                    }
        
        return super(StockPicking, self).button_validate()
    
    def action_force_validate(self):
        """Force validate without SN check"""
        return super(StockPicking, self).button_validate()