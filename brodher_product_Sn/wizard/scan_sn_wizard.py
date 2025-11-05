# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
import logging

_logger = logging.getLogger(__name__)

class ScanSNWizard(models.TransientModel):
    _name = 'scan.sn.wizard'
    _description = 'Scan Serial Number Wizard'
    
    picking_id = fields.Many2one('stock.picking', string='Stock Picking', required=True)
    picking_name = fields.Char(related='picking_id.name', string='Picking')
    picking_type = fields.Selection(related='picking_id.picking_type_code', string='Type')
    
    # Input methods
    input_method = fields.Selection([
        ('scan', 'Scan QR Code'),
        ('manual', 'Select Manually')
    ], string='Input Method', default='scan', required=True)
    
    scanned_sn = fields.Char(
        string='Scan Serial Number', 
        help="Scan QR Code or enter serial number manually"
    )
    
    serial_number_id = fields.Many2one(
        'product.serial.number',
        string='Select Serial Number',
        domain="[('id', 'in', available_sn_ids)]"
    )
    
    available_sn_ids = fields.Many2many(
        'product.serial.number',
        compute='_compute_available_sn_ids',
        string='Available SNs'
    )
    
    move_type = fields.Selection([
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('internal', 'Internal Transfer')
    ], string='Move Type', required=True, default='in')
    
    location_src_id = fields.Many2one('stock.location', string='From')
    location_dest_id = fields.Many2one('stock.location', string='To', required=True)
    
    notes = fields.Text(string='Notes')
    
    # Display info
    sn_info = fields.Html(string='Serial Number Info', compute='_compute_sn_info')
    
    # Summary
    total_scanned = fields.Integer(
        string='Total Scanned',
        compute='_compute_total_scanned'
    )
    
    scanned_list = fields.Html(
        string='Scanned List',
        compute='_compute_scanned_list'
    )
    
    # Expected quantities per product
    expected_quantities = fields.Html(
        string='Expected Quantities',
        compute='_compute_expected_quantities'
    )
    
    @api.depends('picking_id', 'move_type')
    def _compute_available_sn_ids(self):
        """Get available serial numbers based on picking and move type"""
        for wizard in self:
            if not wizard.picking_id:
                wizard.available_sn_ids = [(5, 0, 0)]
                continue
            
            # Get products in this picking
            product_tmpls = wizard.picking_id.move_ids_without_package.mapped('product_id.product_tmpl_id')
            
            domain = [('product_tmpl_id', 'in', product_tmpls.ids)]
            
            # Filter based on move type
            if wizard.move_type == 'out':
                # For outgoing, only show available/reserved SNs
                domain.append(('status', 'in', ['available', 'reserved']))
            elif wizard.move_type == 'in':
                # For incoming, show all SNs (even if used, could be returns)
                pass
            
            # Exclude already scanned in this picking
            already_scanned = wizard.picking_id.sn_move_ids.mapped('serial_number_id.id')
            if already_scanned:
                domain.append(('id', 'not in', already_scanned))
            
            available_sns = self.env['product.serial.number'].search(domain)
            wizard.available_sn_ids = [(6, 0, available_sns.ids)]
    
    @api.depends('picking_id')
    def _compute_total_scanned(self):
        for wizard in self:
            if wizard.picking_id:
                wizard.total_scanned = len(wizard.picking_id.sn_move_ids)
            else:
                wizard.total_scanned = 0
    
    @api.depends('picking_id')
    def _compute_expected_quantities(self):
        """Show expected vs scanned quantities"""
        for wizard in self:
            if wizard.picking_id:
                html = '<div style="margin: 10px 0;">'
                html += '<strong>Products to Scan:</strong>'
                html += '<table class="table table-sm table-bordered" style="margin-top: 5px;">'
                html += '<thead><tr><th>Product</th><th>Expected</th><th>Scanned</th><th>Remaining</th><th>Status</th></tr></thead><tbody>'
                
                for move in wizard.picking_id.move_ids_without_package:
                    product_tmpl = move.product_id.product_tmpl_id
                    
                    # Skip products without SN
                    if not product_tmpl.sn_product_type:
                        continue
                    
                    expected = int(move.product_uom_qty)
                    scanned = len(wizard.picking_id.sn_move_ids.filtered(
                        lambda sm: sm.serial_number_id.product_tmpl_id == product_tmpl
                    ))
                    remaining = expected - scanned
                    
                    if scanned >= expected:
                        status = '<span style="color: green;">✓ Complete</span>'
                        row_style = 'background: #d4edda;'
                    elif scanned > 0:
                        status = '<span style="color: orange;">◐ Partial</span>'
                        row_style = 'background: #fff3cd;'
                    else:
                        status = '<span style="color: red;">○ Pending</span>'
                        row_style = ''
                    
                    html += f'<tr style="{row_style}">'
                    html += f'<td>{product_tmpl.name}</td>'
                    html += f'<td class="text-center">{expected}</td>'
                    html += f'<td class="text-center"><strong>{scanned}</strong></td>'
                    html += f'<td class="text-center"><strong style="color: red;">{remaining}</strong></td>'
                    html += f'<td class="text-center">{status}</td>'
                    html += f'</tr>'
                
                html += '</tbody></table></div>'
                wizard.expected_quantities = html
            else:
                wizard.expected_quantities = ''
    
    @api.depends('picking_id')
    def _compute_scanned_list(self):
        for wizard in self:
            if wizard.picking_id and wizard.picking_id.sn_move_ids:
                html = '<div style="max-height: 150px; overflow-y: auto; margin-top: 10px;">'
                html += '<strong>Recently Scanned:</strong>'
                html += '<table class="table table-sm">'
                html += '<thead><tr><th>SN</th><th>Product</th><th>Time</th><th>User</th></tr></thead><tbody>'
                
                for move in wizard.picking_id.sn_move_ids.sorted(lambda m: m.move_date, reverse=True)[:10]:
                    html += f'<tr>'
                    html += f'<td><code>{move.serial_number_name}</code></td>'
                    html += f'<td><small>{move.product_tmpl_id.name}</small></td>'
                    html += f'<td><small>{move.move_date.strftime("%H:%M:%S")}</small></td>'
                    html += f'<td><small>{move.user_id.name}</small></td>'
                    html += f'</tr>'
                
                html += '</tbody></table></div>'
                wizard.scanned_list = html
            else:
                wizard.scanned_list = '<p class="text-muted"><em>No serial numbers scanned yet</em></p>'
    
    @api.depends('scanned_sn', 'serial_number_id', 'input_method')
    def _compute_sn_info(self):
        for wizard in self:
            sn = None
            
            # Get SN based on input method
            if wizard.input_method == 'scan' and wizard.scanned_sn:
                sn = self.env['product.serial.number'].search([
                    ('name', '=', wizard.scanned_sn)
                ], limit=1)
            elif wizard.input_method == 'manual' and wizard.serial_number_id:
                sn = wizard.serial_number_id
            
            if sn:
                # Check if product is in this picking
                product_in_picking = sn.product_tmpl_id in wizard.picking_id.move_ids_without_package.mapped('product_id.product_tmpl_id')
                
                if not product_in_picking:
                    wizard.sn_info = f"""
                        <div style="padding: 15px; background: #fff3cd; border-radius: 5px; border-left: 4px solid #ffc107;">
                            <h4 style="color: #856404; margin-top: 0;">⚠️ Product Not in Picking</h4>
                            <p>Serial number <strong>{sn.name}</strong> is for product <strong>{sn.product_tmpl_id.name}</strong> which is not in this picking!</p>
                        </div>
                    """
                    return
                
                status_color = {
                    'available': '#d4edda',
                    'reserved': '#fff3cd', 
                    'used': '#f8d7da'
                }.get(sn.status, '#f0f0f0')
                
                wizard.sn_info = f"""
                    <div style="padding: 15px; background: {status_color}; border-radius: 5px; border-left: 4px solid #28a745;">
                        <h4 style="margin-top: 0;">✓ Serial Number Found!</h4>
                        <table class="table table-sm">
                            <tr><td><strong>SN:</strong></td><td><span style="font-family: monospace; font-size: 16px;">{sn.name}</span></td></tr>
                            <tr><td><strong>Product:</strong></td><td>{sn.product_tmpl_id.name}</td></tr>
                            <tr><td><strong>Variant:</strong></td><td>{sn.product_id.name if sn.product_id else 'N/A'}</td></tr>
                            <tr><td><strong>Type:</strong></td><td>{'Man' if sn.sn_type == 'M' else 'Woman'}</td></tr>
                            <tr><td><strong>Status:</strong></td><td><span class="badge">{sn.status.upper()}</span></td></tr>
                            <tr><td><strong>Location:</strong></td><td>{sn.location_id.complete_name if sn.location_id else 'Not Set'}</td></tr>
                            <tr><td><strong>QC:</strong></td><td>{'✓ Passed' if sn.qc_passed else '✗ Failed'}</td></tr>
                        </table>
                    </div>
                """
            elif wizard.input_method == 'scan' and wizard.scanned_sn:
                wizard.sn_info = f"""
                    <div style="padding: 15px; background: #f8d7da; border-radius: 5px; border-left: 4px solid #dc3545;">
                        <h4 style="color: #721c24; margin-top: 0;">✗ Serial Number Not Found!</h4>
                        <p>Serial number <strong>{wizard.scanned_sn}</strong> does not exist in the system.</p>
                        <p><em>Please check the serial number or generate it first.</em></p>
                    </div>
                """
            else:
                wizard.sn_info = """
                    <div style="padding: 15px; background: #e7f3ff; border-radius: 5px; border-left: 4px solid #0d6efd;">
                        <p><strong>📱 Ready to scan or select...</strong></p>
                        <p>Choose scan method or select serial number from dropdown</p>
                    </div>
                """
    
    @api.onchange('input_method')
    def _onchange_input_method(self):
        """Clear fields when switching input method"""
        if self.input_method == 'scan':
            self.serial_number_id = False
        else:
            self.scanned_sn = False
    
    def action_confirm_scan(self):
        """Confirm scanned serial number"""
        self.ensure_one()
        
        # Get SN based on input method
        sn = None
        if self.input_method == 'scan':
            if not self.scanned_sn:
                raise UserError(_('Please scan or enter serial number!'))
            
            sn = self.env['product.serial.number'].search([
                ('name', '=', self.scanned_sn)
            ], limit=1)
            
            if not sn:
                raise ValidationError(_('Serial Number %s not found in the system!') % self.scanned_sn)
        
        else:  # manual
            if not self.serial_number_id:
                raise UserError(_('Please select a serial number!'))
            
            sn = self.serial_number_id
        
        # Check if product is in this picking
        product_in_picking = sn.product_tmpl_id in self.picking_id.move_ids_without_package.mapped('product_id.product_tmpl_id')
        
        if not product_in_picking:
            raise UserError(_(
                'Product "%s" is not in this picking!\n'
                'This picking only contains: %s'
            ) % (
                sn.product_tmpl_id.name,
                ', '.join(self.picking_id.move_ids_without_package.mapped('product_id.product_tmpl_id.name'))
            ))
        
        # Check if already scanned in this picking
        existing = self.env['product.sn.move'].search([
            ('picking_id', '=', self.picking_id.id),
            ('serial_number_id', '=', sn.id)
        ])
        
        if existing:
            raise UserError(_('Serial Number %s has already been scanned for this picking!') % sn.name)
        
        # Validate based on move type
        if self.move_type == 'out':
            if sn.status not in ['available', 'reserved']:
                raise UserError(_(
                    'Serial Number %s is not available for shipment!\n'
                    'Current status: %s'
                ) % (sn.name, sn.status))
        
        # Create movement record
        move_vals = {
            'serial_number_id': sn.id,
            'move_type': self.move_type,
            'location_src_id': self.location_src_id.id if self.location_src_id else False,
            'location_dest_id': self.location_dest_id.id,
            'picking_id': self.picking_id.id,
            'notes': self.notes,
        }
        
        move = self.env['product.sn.move'].create(move_vals)
        
        # Update serial number location and status
        update_vals = {
            'location_id': self.location_dest_id.id,
            'last_move_date': fields.Datetime.now(),
        }
        
        # Update status based on move type
        if self.move_type == 'in':
            update_vals['status'] = 'available'
        elif self.move_type == 'out':
            update_vals['status'] = 'used'
        
        sn.write(update_vals)
        
        _logger.info('✓ SN %s scanned - Method: %s, Picking: %s, Type: %s' % (
            sn.name,
            self.input_method,
            self.picking_id.name,
            self.move_type
        ))
        
        # Return wizard again for next scan (clear fields)
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'scan.sn.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_picking_id': self.picking_id.id,
                'default_move_type': self.move_type,
                'default_location_src_id': self.location_src_id.id if self.location_src_id else False,
                'default_location_dest_id': self.location_dest_id.id,
                'default_input_method': self.input_method,  # Keep same method
            }
        }
    
    def action_done(self):
        """Close wizard and check if all scanned"""
        is_complete, error_msg = self.picking_id._check_sn_scan_completion()
        
        if not is_complete:
            # Show warning
            return {
                'type': 'ir.actions.act_window',
                'res_model': 'sn.validation.wizard',
                'view_mode': 'form',
                'target': 'new',
                'context': {
                    'default_picking_id': self.picking_id.id,
                    'default_warning_message': error_msg,
                }
            }
        
        return {'type': 'ir.actions.act_window_close'}