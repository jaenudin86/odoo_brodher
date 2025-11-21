class ResPartner(models.Model):
    _inherit = 'res.partner'

    # date_of_birth = fields.Date(string='Date of Birth')
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