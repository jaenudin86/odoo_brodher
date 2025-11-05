# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime
import qrcode
import base64
from io import BytesIO
import logging

_logger = logging.getLogger(__name__)

class ProductSerialNumber(models.Model):
    _name = 'product.serial.number'
    _description = 'Product Serial Number'
    _order = 'create_date desc'
    
    name = fields.Char(
        string='Serial Number', 
        required=True, 
        readonly=True,
        copy=False
    )
    
    product_tmpl_id = fields.Many2one(
        'product.template', 
        string='Product Template', 
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product', 
        string='Product Variant',
        ondelete='cascade'
    )
    
    sn_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='Product Type', required=True, readonly=True)
    
    year_code = fields.Char(
        string='Year Code', 
        size=2, 
        required=True, 
        readonly=True
    )
    
    sequence_number = fields.Integer(
        string='Sequence Number', 
        required=True, 
        readonly=True
    )
    
    status = fields.Selection([
        ('available', 'Available'),
        ('used', 'Used'),
        ('reserved', 'Reserved')
    ], string='Status', default='available')
    
    qc_passed = fields.Boolean(string='QC Passed', default=True)
    
    generated_date = fields.Datetime(
        string='Generated Date', 
        default=fields.Datetime.now, 
        readonly=True
    )
    
    qr_code = fields.Binary(
        string='QR Code',
        compute='_compute_qr_code',
        store=True
    )
    
    # Tracking fields
    location_id = fields.Many2one('stock.location', string='Current Location')
    last_move_date = fields.Datetime(string='Last Move Date')
    move_history_ids = fields.One2many('product.sn.move', 'serial_number_id', string='Move History')
    
    _sql_constraints = [
        ('serial_number_unique', 'unique(name)', 
         'Serial Number must be unique!')
    ]
    
    @api.depends('name')
    def _compute_qr_code(self):
        """Generate QR Code untuk serial number"""
        for record in self:
            if record.name:
                try:
                    # Generate QR Code
                    qr = qrcode.QRCode(
                        version=1,
                        error_correction=qrcode.constants.ERROR_CORRECT_L,
                        box_size=10,
                        border=4,
                    )
                    qr.add_data(record.name)
                    qr.make(fit=True)
                    
                    img = qr.make_image(fill_color="black", back_color="white")
                    
                    # Convert to base64
                    buffer = BytesIO()
                    img.save(buffer, format='PNG')
                    qr_code_base64 = base64.b64encode(buffer.getvalue())
                    
                    record.qr_code = qr_code_base64
                except Exception as e:
                    _logger.error('Error generating QR Code: %s' % str(e))
                    record.qr_code = False
            else:
                record.qr_code = False
    
    @api.model
    def _get_next_sequence(self, sn_type, year_code):
        """Get next sequence number for the product type and year"""
        last_sn = self.search([
            ('sn_type', '=', sn_type),
            ('year_code', '=', year_code)
        ], order='sequence_number desc', limit=1)
        
        if last_sn:
            return last_sn.sequence_number + 1
        return 1
    
    @api.model
    def generate_serial_number(self, product_tmpl_id, product_id, sn_type, quantity=1):
        """Generate serial numbers"""
        _logger.info('=== GENERATE SERIAL NUMBER CALLED ===')
        
        product_tmpl = self.env['product.template'].browse(product_tmpl_id)
        
        if not product_tmpl:
            raise ValidationError(_('Product not found!'))
        
        current_year = datetime.now().strftime('%y')
        group_product = 'PF'
        serial_numbers = []
        
        for i in range(quantity):
            next_seq = self._get_next_sequence(sn_type, current_year)
            serial_number = f"{group_product}{current_year}{sn_type}{next_seq:07d}"
            
            vals = {
                'name': serial_number,
                'product_tmpl_id': product_tmpl_id,
                'sn_type': sn_type,
                'year_code': current_year,
                'sequence_number': next_seq,
                'status': 'available',
                'qc_passed': True
            }
            
            if product_id:
                vals['product_id'] = product_id
            
            sn_record = self.create(vals)
            serial_numbers.append(sn_record)
            
            _logger.info('Created SN: %s' % serial_number)
        
        return serial_numbers
    
    def action_print_qr_labels(self):
        """Print QR Code labels"""
        return self.env.ref('product_serial_number.action_report_sn_qr_labels').report_action(self)
    
    def action_export_excel(self):
        """Export serial numbers to Excel"""
        return {
            'type': 'ir.actions.act_url',
            'url': '/web/export_sn_excel/%s' % ','.join(map(str, self.ids)),
            'target': 'new',
        }
    
    def scan_qr_code(self, qr_data):
        """Find serial number by QR code data"""
        sn = self.search([('name', '=', qr_data)], limit=1)
        if not sn:
            raise ValidationError(_('Serial Number %s not found!') % qr_data)
        return sn

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        """Override name_search untuk search lebih baik"""
        args = args or []
        
        if name:
            # Search by name, product name, or product code
            records = self.search([
                '|', '|',
                ('name', operator, name),
                ('product_tmpl_id.name', operator, name),
                ('product_id.default_code', operator, name)
            ] + args, limit=limit)
        else:
            records = self.search(args, limit=limit)
        
        return records.name_get()
    
    def name_get(self):
        """Override name_get untuk display lebih informatif"""
        result = []
        for record in self:
            name = f"{record.name} - {record.product_tmpl_id.name}"
            if record.product_id:
                name += f" ({record.product_id.display_name})"
            name += f" [{record.status.upper()}]"
            result.append((record.id, name))
        return result
# Model untuk tracking perpindahan SN
class ProductSNMove(models.Model):
    _name = 'product.sn.move'
    _description = 'Product Serial Number Movement'
    _order = 'move_date desc'
    
    serial_number_id = fields.Many2one('product.serial.number', string='Serial Number', required=True, ondelete='cascade')
    move_type = fields.Selection([
        ('in', 'Stock In'),
        ('out', 'Stock Out'),
        ('internal', 'Internal Transfer')
    ], string='Move Type', required=True)
    
    location_src_id = fields.Many2one('stock.location', string='Source Location')
    location_dest_id = fields.Many2one('stock.location', string='Destination Location')
    move_date = fields.Datetime(string='Move Date', default=fields.Datetime.now)
    user_id = fields.Many2one('res.users', string='User', default=lambda self: self.env.user)
    notes = fields.Text(string='Notes')
    
    picking_id = fields.Many2one('stock.picking', string='Stock Picking')