# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError
from datetime import datetime

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
    
    _sql_constraints = [
        ('serial_number_unique', 'unique(name)', 
         'Serial Number must be unique!')
    ]
    
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
        import logging
        _logger = logging.getLogger(__name__)
        
        _logger.info('=== GENERATE SERIAL NUMBER CALLED ===')
        _logger.info('Product Template ID: %s' % product_tmpl_id)
        _logger.info('Product Variant ID: %s' % product_id)
        _logger.info('SN Type: %s' % sn_type)
        _logger.info('Quantity: %s' % quantity)
        
        product_tmpl = self.env['product.template'].browse(product_tmpl_id)
        
        if not product_tmpl:
            _logger.error('Product Template not found!')
            raise ValidationError(_('Product not found!'))
        
        _logger.info('Product Template found: %s' % product_tmpl.name)
        
        current_year = datetime.now().strftime('%y')
        group_product = 'PF'
        serial_numbers = []
        
        for i in range(quantity):
            next_seq = self._get_next_sequence(sn_type, current_year)
            serial_number = f"{group_product}{current_year}{sn_type}{next_seq:07d}"
            
            _logger.info('Creating SN #%d: %s' % (i+1, serial_number))
            
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
                _logger.info('Adding product variant ID: %s' % product_id)
            
            try:
                sn_record = self.create(vals)
                serial_numbers.append(sn_record)
                _logger.info('Successfully created SN ID: %s' % sn_record.id)
            except Exception as e:
                _logger.error('Error creating SN: %s' % str(e))
                raise
        
        _logger.info('=== TOTAL GENERATED: %d ===' % len(serial_numbers))
        
        return serial_numbers