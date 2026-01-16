# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime
import re

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    ingredients = fields.Text(string="Ingredients")
    brand = fields.Char(string="Brand")
    size = fields.Char(string="Size")
    is_article = fields.Boolean(string='Is Article', default=False)

    gross_weight = fields.Float(string='Gross Weight')
    net_weight = fields.Float(string='Net Weight')
    net_net_weight = fields.Float(string='Net Net Weight')
    base_colour = fields.Char(string='Base Colour')
    text_colour = fields.Char(string='Text Colour')

    def _generate_article_number(self, is_article):
        """
        - ATC: ATC + DD + MM + YY + XXX (12 Digit)
        - PSIT: PSIT + YY + XXXX (10 Digit)
        """
        now = datetime.today()
        ctx = dict(self._context, ir_sequence_date=now.strftime('%Y-%m-%d'))
        
        if is_article:
            prefix = 'ATC'
            date_str = now.strftime('%d%m%y')
            seq_code = 'article.number.sequence'
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code(seq_code) or '001'
            return f"{prefix}{date_str}{seq}"
        else:
            prefix = 'PSIT'
            year_str = now.strftime('%y')
            seq_code = 'pist.number.sequence'
            seq = self.env['ir.sequence'].with_context(ctx).next_by_code(seq_code) or '0001'
            return f"{prefix}{year_str}{seq}"

    @api.model
    def create(self, vals):
        # Template tidak membuat barcode/default_code (hanya di variant)
        return super(ProductTemplate, self).create(vals)
    def _generate_article_number(self, is_article):
        """Generate default_code:
        - ATC + DD + MM + YY + Seq(3) jika Is Article = True
        - PSIT + DD + MM + YY + Seq(3) jika Is Article = False
        """
        today = datetime.today()
        date_str = today.strftime('%d')
        month_str = today.strftime('%m')
        year_str = today.strftime('%y')

        prefix = 'ATC' if is_article else 'PSIT'
        seq_code = 'article.number.sequence' if is_article else 'pist.number.sequence'

        # Ambil nomor urut dari ir.sequence
        sequence = self.env['ir.sequence'].next_by_code(seq_code)
        if not sequence:
            sequence = '001'

        return f"{prefix}{date_str}{month_str}{year_str}{sequence}"

class ResPartner(models.Model):
    _inherit = 'res.partner'

    date_of_birth = fields.Date(string='Date of Birth')
     # Supplier Info
    supplier_id_ktp = fields.Char(string="Supplier ID / KTP")
    supplier_product = fields.Char(string="Supplier Product")
    contact_head_pic_name = fields.Char(string="Contact Head PIC Name")
    contact_head_pic_mobile = fields.Char(string="Mobile Phone (Head PIC)")
    contact_pic1_name = fields.Char(string="Contact PIC 1 Name")
    contact_pic1_mobile = fields.Char(string="Mobile Phone (PIC 1)")
    contact_pic2_name = fields.Char(string="Contact PIC 2 Name")
    contact_pic2_mobile = fields.Char(string="Mobile Phone (PIC 2)")

    fax = fields.Char(string="Fax")
    factory_address = fields.Char(string="Factory Address")
    factory_city = fields.Char(string="City")
    factory_state = fields.Char(string="State")
    factory_postal = fields.Char(string="Postal Code")
    factory_country = fields.Char(string="Country")
    factory_phone = fields.Char(string="Phone")
    factory_fax2 = fields.Char(string="Fax 2")

    supplier_status = fields.Selection([
        ('active', 'Active'),
        ('inactive', 'Inactive'),
    ], string="Status", default="active")

    company_profile = fields.Binary(string="Company Profile")

    # Bank / Account Info (Supplier)
    bank_currency = fields.Many2one('res.currency', string="Currency")
    bank_swift = fields.Char(string="Swift Code / Branch")
    bank_city = fields.Char(string="Bank City")
    bank_country = fields.Char(string="Bank Country")
    beneficiary_name = fields.Char(string="Beneficiary Name")

    # NPWP (after Tax ID)
    npwp_name = fields.Char(string="NPWP Name")
    npwp_address = fields.Char(string="NPWP Address")