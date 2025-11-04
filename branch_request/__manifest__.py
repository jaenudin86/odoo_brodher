# -*- coding: utf-8 -*-
{
    'name': 'Branch Request Management',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Manage inter-branch product requests and transfers',
    'description': """
        Branch Request Management System for Odoo 18
        ==============================================
        * Request products from other branches
        * Approve/reject branch requests  
        * Track transfers between branches
        * Automatic stock movements
        * Inherit from Internal Transfer (stock.picking)
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['stock', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/sequence.xml',
        'views/branch_request_views.xml',
        'views/stock_picking_views.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}