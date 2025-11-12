# -*- coding: utf-8 -*-
{
    'name': "Purchase Request",

    'summary': "Employee Purchase Requisition.",
    'license': 'Other proprietary',
    'author': "trijya technologies",
    'website': "https://www.trijya.com",
    'category': 'Uncategorized',
    'version':'18.0.1.0.0',

    # any module necessary for this one to work correctly
    'depends': ['base', 'mail', 'hr', 'product', 'purchase'],
    'images': ['static/description/banner.png'],
    # always loaded
    'data': ['security/security.xml',
        'security/ir.model.access.csv',
        'views/requisition_view.xml',
        'views/report_purchase_requisition.xml',
        'views/site_request_material.xml',
        'views/partner_form_inherit.xml',
        'views/views.xml',
        'data/ir_sequence_purchase_requestion.xml'],
    'installable': True,
    'application': True,
}

