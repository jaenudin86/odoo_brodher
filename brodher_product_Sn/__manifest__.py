{
    'name': 'Product Serial Number Generator',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Generate Serial Number with QR Code and Scanning',
    'depends': ['product', 'stock', 'purchase', 'sale'],
    'external_dependencies': {
        'python': ['qrcode'],
    },
    'data': [
        'security/ir.model.access.csv',
        'wizard/product_sn_wizard_views.xml',
        'wizard/message_wizard_views.xml',
        'wizard/scan_sn_wizard_views.xml',
        'wizard/sn_validation_wizard_views.xml',  # TAMBAHKAN
        'views/product_template_views.xml',
        'views/serial_number_views.xml',
        'views/sn_move_views.xml',
        'views/stock_picking_views.xml',
        # 'reports/sn_qr_label_report.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}