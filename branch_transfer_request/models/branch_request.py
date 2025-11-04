from odoo import models, fields, api
from odoo.exceptions import UserError

class BranchRequest(models.Model):
    _name = "branch.request"
    _description = "Branch Request"

    name = fields.Char(string="Request Reference", required=True, copy=False, readonly=True,
                       default=lambda self: 'New')
    request_date = fields.Datetime(string="Request Date", default=fields.Datetime.now, readonly=True)
    source_branch_id = fields.Many2one("res.company", string="Source Branch", required=True,
                                       default=lambda self: self.env.company)
    dest_branch_id = fields.Many2one("res.company", string="Destination Branch", required=True)
    
    # New field to link to the created Stock Picking (Internal Transfer)
    picking_id = fields.Many2one('stock.picking', string='Transfer Picking', readonly=True, copy=False)
    
    # Computed field for the Smart Button
    picking_count = fields.Integer(compute='_compute_picking_count', string='Picking Count')
    
    state = fields.Selection([
        ("draft", "Draft"),
        ("approved", "Approved"),
        ("done", "Done"),
        ("cancel", "Cancelled"),
    ], default="draft", string="Status")

    line_ids = fields.One2many("branch.request.line", "request_id", string="Products")

    @api.depends('picking_id')
    def _compute_picking_count(self):
        for record in self:
            record.picking_count = 1 if record.picking_id else 0

    @api.model
    def create(self, vals):
        if vals.get('name', 'New') == 'New':
            vals['name'] = self.env['ir.sequence'].next_by_code('branch.request') or 'New'
        return super().create(vals)

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_cancel(self):
        self.write({'state': 'cancel'})

    def action_done(self):
        """
        Creates an internal stock picking (transfer) from the source branch to the destination branch.
        """
        self.ensure_one()
        if not self.line_ids:
            raise UserError("Cannot set to done without any products requested.")
            
        if self.picking_id:
            # If picking already exists, just update state
            self.write({'state': 'done'})
            return True

        # 1. Get Source and Destination Locations and Picking Type
        
        # --- Source Branch Logic ---
        source_warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.source_branch_id.id)
        ], limit=1)
        if not source_warehouse:
            raise UserError("No default warehouse found for the Source Branch: %s. Please configure a warehouse for this company." % self.source_branch_id.name)
        source_location_id = source_warehouse.lot_stock_id.id

        # Internal Transfer Picking Type
        picking_type = self.env['stock.picking.type'].search([
            ('code', '=', 'internal'),
            ('warehouse_id', '=', source_warehouse.id),
        ], limit=1)
        if not picking_type:
            raise UserError("Internal Transfer Picking Type not found for the Source Branch (%s)." % self.source_branch_id.name)

        # --- Destination Branch Logic ---
        dest_warehouse = self.env['stock.warehouse'].search([
            ('company_id', '=', self.dest_branch_id.id)
        ], limit=1)
        if not dest_warehouse:
            # We assume the destination is the default stock location of the destination branch's warehouse
            raise UserError("No default warehouse found for the Destination Branch: %s. Please configure a warehouse for this company." % self.dest_branch_id.name)
        dest_location_id = dest_warehouse.lot_stock_id.id


        # 2. Prepare Stock Move Lines
        move_lines = []
        for line in self.line_ids:
            move_lines.append((0, 0, {
                'name': line.product_id.display_name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_uom_qty,
                'product_uom': line.product_uom.id,
                'location_id': source_location_id,
                'location_dest_id': dest_location_id,
                'company_id': self.source_branch_id.id,
                'origin': self.name,
            }))

        # 3. Create Stock Picking Header
        picking_vals = {
            'picking_type_id': picking_type.id,
            'location_id': source_location_id,
            'location_dest_id': dest_location_id,
            'move_ids_without_package': move_lines,
            'company_id': self.source_branch_id.id,
            'origin': self.name,
            'branch_request_id': self.id, # Custom field to link back (optional, but good practice)
        }
        
        new_picking = self.env['stock.picking'].create(picking_vals)
        
        # 4. Link the Picking and Update State
        self.write({
            'state': 'done',
            'picking_id': new_picking.id,
        })
        
        return True

    def action_view_picking(self):
        """Action to open the linked stock picking document."""
        self.ensure_one()
        return {
            'name': ('Transfer Picking'),
            'type': 'ir.actions.act_window',
            'res_model': 'stock.picking',
            'view_mode': 'form',
            'res_id': self.picking_id.id,
            'target': 'current',
        }


class BranchRequestLine(models.Model):
    _name = "branch.request.line"
    _description = "Branch Request Line"

    request_id = fields.Many2one("branch.request", string="Request", ondelete="cascade")
    product_id = fields.Many2one("product.product", string="Product", required=True)
    product_uom_qty = fields.Float(string="Quantity", required=True, default=1.0)
    product_uom = fields.Many2one("uom.uom", string="Unit of Measure", required=True,
                                  domain="[('category_id', '=', product_id.uom_id.category_id)]")
