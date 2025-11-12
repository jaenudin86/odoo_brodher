# -*- coding: utf-8 -*-
{
    'name': 'Internal Transfer Request',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Inventory',
    'summary': 'Request internal transfers between warehouses with approval workflow',
    'description': """
        Internal Transfer Request Management
        =====================================
        * Request transfer dari cabang ke pusat atau sebaliknya
        * Approval workflow
        * Barcode scanning support
        * Picking dan Put Away process
        * Multi-warehouse support
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'depends': [
        'base',
        'stock',
        'mail',
    ],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        # 'data/sequence.xml',
        'views/branch_request_views.xml',
        # 'views/stock_picking_views.xml',
    ],
    'demo': [],
    'installable': True,
    'application': True,
    'auto_install': False,
    'license': 'LGPL-3',
}