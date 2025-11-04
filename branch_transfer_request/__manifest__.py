{
    'name': 'Branch Transfer Request',
    'version': '1.0',
    'category': 'Inventory',
    'summary': 'Request barang antar cabang dengan approval',
    'author': 'Custom Dev',
    'depends': ['stock', 'product'],
    'data': [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'views/branch_request_views.xml',
    ],
    'installable': True,
    'application': True,
}
