# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class ProductSNWizard(models.TransientModel):
    _name = 'product.sn.wizard'
    _description = 'Product Serial Number Generation Wizard'
    
    product_tmpl_id = fields.Many2one(
        'product.template', 
        string='Product Template', 
        required=True
    )
    
    product_id = fields.Many2one(
        'product.product', 
        string='Product Variant'
    )
    
    sn_type = fields.Selection([
        ('M', 'Man'),
        ('W', 'Woman')
    ], string='Product Type', required=True)
    
    quantity = fields.Integer(
        string='Quantity to Generate', 
        default=1, 
        required=True
    )
    
    preview_sn = fields.Char(
        string='Preview Serial Number',
        compute='_compute_preview_sn',
        store=False
    )
    
    @api.depends('sn_type', 'quantity')
    def _compute_preview_sn(self):
        for record in self:
            if record.sn_type:
                try:
                    year = datetime.now().strftime('%y')
                    SerialNumber = self.env['product.serial.number']
                    next_seq = SerialNumber._get_next_sequence(
                        record.sn_type, 
                        year
                    )
                    
                    preview = f"PF{year}{record.sn_type}{next_seq:07d}"
                    
                    if record.quantity > 1:
                        last_seq = next_seq + record.quantity - 1
                        preview += f" ... PF{year}{record.sn_type}{last_seq:07d}"
                    
                    record.preview_sn = preview
                except:
                    record.preview_sn = 'Preview not available'
            else:
                record.preview_sn = ''
    
    def action_generate(self):
        """Generate serial numbers"""
        _logger.info('=' * 50)
        _logger.info('ACTION GENERATE STARTED')
        _logger.info('=' * 50)
        
        for wizard in self:
            _logger.info('Processing wizard ID: %s' % wizard.id)
            _logger.info('Product Template: %s (ID: %s)' % (wizard.product_tmpl_id.name, wizard.product_tmpl_id.id))
            _logger.info('Product Variant: %s' % (wizard.product_id.name if wizard.product_id else 'None'))
            _logger.info('SN Type: %s' % wizard.sn_type)
            _logger.info('Quantity: %s' % wizard.quantity)
            
            # Validasi
            if wizard.quantity <= 0:
                raise UserError(_('Quantity must be greater than 0!'))
            
            if wizard.quantity > 1000:
                raise UserError(_('Cannot generate more than 1000 serial numbers at once!'))
            
            # Generate Serial Numbers
            try:
                SerialNumber = self.env['product.serial.number']
                
                _logger.info('Calling generate_serial_number...')
                
                serial_numbers = SerialNumber.generate_serial_number(
                    wizard.product_tmpl_id.id,
                    wizard.product_id.id if wizard.product_id else False,
                    wizard.sn_type,
                    wizard.quantity
                )
                
                _logger.info('Generated %d serial numbers' % len(serial_numbers))
                
                # List generated SNs
                sn_names = [sn.name for sn in serial_numbers]
                _logger.info('Serial Numbers: %s' % ', '.join(sn_names))
                
                # Prepare message
                if len(serial_numbers) <= 10:
                    sn_list = '\n'.join(sn_names)
                else:
                    sn_list = '\n'.join(sn_names[:10]) + f'\n... and {len(serial_numbers) - 10} more'
                
                # Show success message using wizard message
                message_id = self.env['message.wizard'].create({
                    'message': _(
                        'Successfully generated %d serial numbers:\n\n%s'
                    ) % (len(serial_numbers), sn_list)
                })
                
                _logger.info('=' * 50)
                _logger.info('ACTION GENERATE COMPLETED SUCCESSFULLY')
                _logger.info('=' * 50)
                
                return {
                    'name': _('Success'),
                    'type': 'ir.actions.act_window',
                    'res_model': 'message.wizard',
                    'res_id': message_id.id,
                    'view_mode': 'form',
                    'target': 'new',
                }
                
            except Exception as e:
                _logger.error('=' * 50)
                _logger.error('ERROR IN ACTION GENERATE')
                _logger.error('Error: %s' % str(e))
                _logger.error('=' * 50)
                import traceback
                _logger.error(traceback.format_exc())
                raise UserError(_('Error generating serial numbers:\n%s') % str(e))


# Message Wizard untuk menampilkan hasil
class MessageWizard(models.TransientModel):
    _name = 'message.wizard'
    _description = 'Message Wizard'
    
    message = fields.Text(string='Message', readonly=True)