# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class BranchRequest(models.Model):
    _name = 'branch.request'
    _description = 'Branch Product Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New')
    )
    
    requesting_branch_id = fields.Many2one(
        'res.company',
        string='Requesting Branch',
        required=True,
        default=lambda self: self.env.company,
        tracking=True
    )
    
    target_branch_id = fields.Many2one(
        'res.company',
        string='Target Branch (Supplier)',
        required=True,
        tracking=True
    )
    
    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    
    expected_date = fields.Datetime(
        string='Expected Delivery Date',
        required=True,
        tracking=True
    )
    
    note = fields.Text(string='Notes')
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('in_transit', 'In Transit'),
        ('received', 'Received'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', tracking=True, required=True)
    
    line_ids = fields.One2many(
        'branch.request.line',
        'request_id',
        string='Products',
        copy=True
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Internal Transfer',
        readonly=True,
        copy=False
    )
    
    user_id = fields.Many2one(
        'res.users',
        string='Requested By',
        default=lambda self: self.env.user,
        tracking=True
    )
    
    approved_by = fields.Many2one(
        'res.users',
        string='Approved By',
        readonly=True,
        tracking=True
    )
    
    approved_date = fields.Datetime(
        string='Approval Date',
        readonly=True
    )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('branch.request') or _('New')
        return super().create(vals_list)

    def action_send_request(self):
        """Send request to target branch"""
        self.ensure_one()
        if not self.line_ids:
            raise UserError(_('Please add at least one product line.'))
        
        self.write({'state': 'requested'})
        self.message_post(
            body=_('Branch request sent to %s', self.target_branch_id.name),
            subtype_xmlid='mail.mt_note'
        )

    def action_approve(self):
        """Approve request and create internal transfer"""
        self.ensure_one()
        if self.state != 'requested':
            raise UserError(_('Only requested orders can be approved.'))
        
        picking = self._create_internal_transfer()
        
        self.write({
            'state': 'approved',
            'approved_by': self.env.user.id,
            'approved_date': fields.Datetime.now(),
            'picking_id': picking.id,
        })
        
        self.message_post(
            body=_('Request approved. Internal transfer %s created.', picking.name),
            subtype_xmlid='mail.mt_note'
        )

    def action_reject(self):
        """Reject the request"""
        self.ensure_one()
        if self.state != 'requested':
            raise UserError(_('Only requested orders can be rejected.'))
        
        self.write({'state': 'rejected'})
        self.message_post(
            body=_('Request rejected.'),
            subtype_xmlid='mail.mt_note'
        )

    def action_cancel(self):
        """Cancel the request"""
        self.ensure_one()
        if self.state in ('received', 'in_transit'):
            raise UserError(_('Cannot cancel a request that is already in transit or received.'))
        
        if self.picking_id and self.picking_id.state not in ('done', 'cancel'):
            self.picking_id.action_cancel()
        
        self.write({'state': 'cancelled'})

    def action_view_transfer(self):
        """View the related internal transfer"""
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Internal Transfer'),
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id,
            'view_mode': 'form',
            'target': 'current',
        }

    def _create_internal_transfer(self):
        """Create internal transfer from branch request"""
        self.ensure_one()
        
        # Get internal transfer operation type
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id.company_id', '=', self.target_branch_id.id),
        ], limit=1)
        
        if not picking_type:
            raise UserError(_('No internal operation type found for company %s', self.target_branch_id.name))
        
        # Get source and destination locations
        source_location = picking_type.default_location_src_id
        dest_location = self.env['stock.location'].search([
            ('company_id', '=', self.requesting_branch_id.id),
            ('usage', '=', 'internal'),
        ], limit=1)
        
        if not dest_location:
            raise UserError(_('No internal location found for requesting branch %s', self.requesting_branch_id.name))
        
        # Create picking
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': source_location.id,
            'location_dest_id': dest_location.id,
            'origin': self.name,
            'scheduled_date': self.expected_date,
            'branch_request_id': self.id,
            'company_id': self.target_branch_id.id,
        }
        
        picking = self.env['stock.picking'].create(picking_vals)
        
        # Create move lines
        for line in self.line_ids:
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity,
                'product_uom': line.product_id.uom_id.id,
                'picking_id': picking.id,
                'location_id': source_location.id,
                'location_dest_id': dest_location.id,
                'company_id': self.target_branch_id.id,
            }
            self.env['stock.move'].create(move_vals)
        
        picking.action_confirm()
        return picking


class BranchRequestLine(models.Model):
    _name = 'branch.request.line'
    _description = 'Branch Request Line'

    request_id = fields.Many2one(
        'branch.request',
        string='Branch Request',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain=[('type', 'in', ['product', 'consu'])]
    )
    
    quantity = fields.Float(
        string='Quantity',
        required=True,
        default=1.0,
        digits='Product Unit of Measure'
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        related='product_id.uom_id',
        readonly=True
    )
    
    note = fields.Char(string='Note')
    
    state = fields.Selection(
        related='request_id.state',
        string='Status',
        readonly=True
    )

    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id