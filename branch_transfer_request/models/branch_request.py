# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError


class InternalTransferRequest(models.Model):
    _name = 'internal.transfer.request'
    _description = 'Internal Transfer Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'create_date desc'

    name = fields.Char(
        string='Request Number',
        required=True,
        copy=False,
        readonly=True,
        index=True,
        default=lambda self: _('New')
    )
    
    request_date = fields.Datetime(
        string='Request Date',
        default=fields.Datetime.now,
        required=True,
        tracking=True
    )
    
    requester_id = fields.Many2one(
        'res.users',
        string='Requester',
        default=lambda self: self.env.user,
        required=True,
        tracking=True
    )
    
    source_location_id = fields.Many2one(
        'stock.location',
        string='Source Location',
        required=True,
        tracking=True,
        domain="[('usage', '=', 'internal')]"
    )
    
    destination_location_id = fields.Many2one(
        'stock.location',
        string='Destination Location',
        required=True,
        tracking=True,
        domain="[('usage', '=', 'internal')]"
    )
    
    source_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Source Warehouse',
        compute='_compute_warehouses',
        store=True
    )
    
    destination_warehouse_id = fields.Many2one(
        'stock.warehouse',
        string='Destination Warehouse',
        compute='_compute_warehouses',
        store=True
    )
    
    state = fields.Selection([
        ('draft', 'Draft'),
        ('submitted', 'Waiting Approval'),
        ('approved', 'Approved'),
        ('picking', 'Picking in Progress'),
        ('in_transit', 'In Transit'),
        ('received', 'Received'),
        ('put_away', 'Put Away Done'),
        ('done', 'Done'),
        ('rejected', 'Rejected'),
        ('cancelled', 'Cancelled')
    ], string='Status', default='draft', tracking=True, copy=False)
    
    line_ids = fields.One2many(
        'internal.transfer.request.line',
        'request_id',
        string='Request Lines'
    )
    
    approver_id = fields.Many2one(
        'res.users',
        string='Approver',
        tracking=True
    )
    
    approval_date = fields.Datetime(
        string='Approval Date',
        tracking=True
    )
    
    rejection_reason = fields.Text(
        string='Rejection Reason'
    )
    
    picking_id = fields.Many2one(
        'stock.picking',
        string='Delivery Order',
        readonly=True,
        copy=False
    )
    
    putaway_id = fields.Many2one(
        'stock.picking',
        string='Put Away Receipt',
        readonly=True,
        copy=False
    )
    
    notes = fields.Text(
        string='Notes'
    )
    
    company_id = fields.Many2one(
        'res.company',
        string='Company',
        default=lambda self: self.env.company
    )
    
    priority = fields.Selection([
        ('0', 'Normal'),
        ('1', 'Urgent')
    ], string='Priority', default='0')
    
    @api.depends('source_location_id', 'destination_location_id')
    def _compute_warehouses(self):
        for record in self:
            if record.source_location_id:
                record.source_warehouse_id = self.env['stock.warehouse'].search([
                    ('lot_stock_id', 'parent_of', record.source_location_id.id)
                ], limit=1)
            if record.destination_location_id:
                record.destination_warehouse_id = self.env['stock.warehouse'].search([
                    ('lot_stock_id', 'parent_of', record.destination_location_id.id)
                ], limit=1)
    
    @api.model
    def create(self, vals):
        if vals.get('name', _('New')) == _('New'):
            vals['name'] = self.env['ir.sequence'].next_by_code('internal.transfer.request') or _('New')
        return super(InternalTransferRequest, self).create(vals)
    
    def action_submit(self):
        """Submit request for approval"""
        if not self.line_ids:
            raise UserError(_('Please add at least one product line.'))
        
        for line in self.line_ids:
            if line.quantity_requested <= 0:
                raise UserError(_('Quantity must be greater than zero.'))
        
        self.write({'state': 'submitted'})
        self.message_post(body=_('Request submitted for approval.'))
        
        # Send notification to approvers
        self._notify_approvers()
    
    def action_approve(self):
        """Approve the request and create picking"""
        self.write({
            'state': 'approved',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        
        # Create picking for delivery
        self._create_picking()
        
        self.message_post(body=_('Request approved by %s') % self.env.user.name)
    
    def action_reject(self):
        """Reject the request"""
        if not self.rejection_reason:
            raise UserError(_('Please provide a rejection reason.'))
        
        self.write({
            'state': 'rejected',
            'approver_id': self.env.user.id,
            'approval_date': fields.Datetime.now()
        })
        
        self.message_post(body=_('Request rejected: %s') % self.rejection_reason)
    
    def action_cancel(self):
        """Cancel the request"""
        if self.state in ['done', 'put_away']:
            raise UserError(_('Cannot cancel a completed request.'))
        
        self.write({'state': 'cancelled'})
        
        # Cancel related pickings
        if self.picking_id and self.picking_id.state not in ['done', 'cancel']:
            self.picking_id.action_cancel()
        if self.putaway_id and self.putaway_id.state not in ['done', 'cancel']:
            self.putaway_id.action_cancel()
    
    def action_view_picking(self):
        """View the delivery picking"""
        self.ensure_one()
        return {
            'name': _('Delivery Order'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }
    
    def action_view_putaway(self):
        """View the putaway receipt"""
        self.ensure_one()
        return {
            'name': _('Put Away Receipt'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.putaway_id.id,
            'target': 'current',
        }
    
    def _create_picking(self):
        """Create stock picking for internal transfer"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', self.source_warehouse_id.id)
        ], limit=1)
        
        if not picking_type:
            raise UserError(_('No internal picking type found for source warehouse.'))
        
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': self.source_location_id.id,
            'location_dest_id': self.destination_location_id.id,
            'origin': self.name,
            'user_id': self.requester_id.id,
            'move_ids': []
        }
        
        # Create move lines
        for line in self.line_ids:
            move_vals = {
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.quantity_requested,
                'product_uom': line.product_uom_id.id,
                'location_id': self.source_location_id.id,
                'location_dest_id': self.destination_location_id.id,
                'picking_type_id': picking_type.id,
            }
            picking_vals['move_ids'].append((0, 0, move_vals))
        
        picking = self.env['stock.picking'].create(picking_vals)
        picking.action_confirm()
        
        self.picking_id = picking.id
        self.message_post(body=_('Picking %s created.') % picking.name)
    
    def _notify_approvers(self):
        """Send notification to approvers"""
        # Get approver group
        group = self.env.ref('stock.group_stock_manager', raise_if_not_found=False)
        if group:
            users = group.users
            for user in users:
                self.activity_schedule(
                    'mail.mail_activity_data_todo',
                    user_id=user.id,
                    summary=_('Approval Required: %s') % self.name
                )
    
    def _check_picking_state(self):
        """Check picking state and update request state"""
        for record in self:
            if record.picking_id and record.picking_id.state == 'done':
                if record.state != 'in_transit':
                    record.write({'state': 'in_transit'})
                    # Create putaway picking
                    record._create_putaway()
    
    def _create_putaway(self):
        """Create putaway receipt"""
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', self.destination_warehouse_id.id)
        ], limit=1)
        
        if not picking_type:
            return
        
        # Putaway is automatic after receiving
        self.message_post(body=_('Goods ready for put away at destination.'))
    
    @api.model
    def _cron_check_pickings(self):
        """Cron job to check picking states"""
        requests = self.search([('state', 'in', ['approved', 'picking', 'in_transit'])])
        for request in requests:
            request._check_picking_state()


class InternalTransferRequestLine(models.Model):
    _name = 'internal.transfer.request.line'
    _description = 'Internal Transfer Request Line'

    request_id = fields.Many2one(
        'internal.transfer.request',
        string='Transfer Request',
        required=True,
        ondelete='cascade'
    )
    
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        required=True,
        domain="[('type', '!=', 'service')]"
    )
    
    product_uom_id = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        required=True
    )
    
    quantity_requested = fields.Float(
        string='Quantity Requested',
        required=True,
        default=1.0
    )
    
    quantity_available = fields.Float(
        string='Available Quantity',
        compute='_compute_quantity_available'
    )
    
    barcode = fields.Char(
        related='product_id.barcode',
        string='Barcode',
        readonly=True
    )
    
    notes = fields.Char(
        string='Notes'
    )
    
    @api.onchange('product_id')
    def _onchange_product_id(self):
        if self.product_id:
            self.product_uom_id = self.product_id.uom_id.id
    
    @api.depends('product_id', 'request_id.source_location_id')
    def _compute_quantity_available(self):
        for line in self:
            if line.product_id and line.request_id.source_location_id:
                quants = self.env['stock.quant'].search([
                    ('product_id', '=', line.product_id.id),
                    ('location_id', '=', line.request_id.source_location_id.id)
                ])
                line.quantity_available = sum(quants.mapped('quantity'))
            else:
                line.quantity_available = 0.0


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    internal_request_id = fields.Many2one(
        'internal.transfer.request',
        string='Internal Request',
        compute='_compute_internal_request',
        store=True
    )
    
    @api.depends('origin')
    def _compute_internal_request(self):
        for picking in self:
            if picking.origin:
                request = self.env['internal.transfer.request'].search([
                    ('name', '=', picking.origin)
                ], limit=1)
                picking.internal_request_id = request.id if request else False
    
    def button_validate(self):
        """Override to update internal request state"""
        res = super(StockPicking, self).button_validate()
        
        # Update internal request state
        for picking in self:
            if picking.internal_request_id:
                if picking.picking_type_code == 'internal':
                    if picking.internal_request_id.state == 'approved':
                        picking.internal_request_id.write({'state': 'in_transit'})
                    elif picking.internal_request_id.state == 'in_transit':
                        picking.internal_request_id.write({'state': 'received'})
        
        return res


class StockMove(models.Model):
    _inherit = 'stock.move'
    
    def _action_done(self, cancel_backorder=False):
        """Override to handle barcode scanning"""
        res = super(StockMove, self)._action_done(cancel_backorder=cancel_backorder)
        
        # Check if all moves in picking are done
        for move in self:
            if move.picking_id and move.picking_id.internal_request_id:
                if all(m.state == 'done' for m in move.picking_id.move_ids):
                    request = move.picking_id.internal_request_id
                    if request.picking_id == move.picking_id:
                        request.write({'state': 'done'})
                        request.message_post(body=_('All items picked and transferred.'))
        
        return res