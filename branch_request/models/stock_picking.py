# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    branch_request_id = fields.Many2one(
        'branch.request',
        string='Branch Request',
        readonly=True,
        copy=False
    )
    
    is_branch_transfer = fields.Boolean(
        string='Is Branch Transfer',
        compute='_compute_is_branch_transfer',
        store=True
    )

    @api.depends('branch_request_id')
    def _compute_is_branch_transfer(self):
        for picking in self:
            picking.is_branch_transfer = bool(picking.branch_request_id)

    def button_validate(self):
        """Override to update branch request status when shipping"""
        res = super().button_validate()
        
        for picking in self:
            if picking.branch_request_id and picking.state == 'done':
                if picking.picking_type_code == 'internal':
                    # Update to in_transit when shipped from supplier branch
                    if picking.branch_request_id.state == 'approved':
                        picking.branch_request_id.write({'state': 'in_transit'})
                        picking.branch_request_id.message_post(
                            body=_('Products shipped via %s', picking.name),
                            subtype_xmlid='mail.mt_note'
                        )
        
        return res

    def _action_done(self):
        """Override to update branch request status when receiving"""
        res = super()._action_done()
        
        for picking in self:
            if picking.branch_request_id and picking.state == 'done':
                # Check if this is the receiving transfer at requesting branch
                if picking.location_dest_id.company_id == picking.branch_request_id.requesting_branch_id:
                    picking.branch_request_id.write({'state': 'received'})
                    picking.branch_request_id.message_post(
                        body=_('Products received at %s', picking.location_dest_id.name),
                        subtype_xmlid='mail.mt_note'
                    )
        
        return res