# -*- coding: utf-8 -*-
{
    'name': 'Product Serial Number Generator',
    'version': '18.0.1.0.0',
    'category': 'Inventory',
    'summary': 'Generate Serial Number for Products with Auto Reset per Year',
    'description': """
        Generate Serial Number otomatis untuk produk
        - Format: PF + 2 digit tahun + M/W + 7 digit nomor urut
        - Auto reset nomor urut setiap awal tahun
        - Terpisah counter untuk Man (M) dan Woman (W)
    """,
    'depends': ['product', 'stock'],
    'data': [
        # 'security/ir.model.access.csv',
        'wizard/product_sn_wizard_views.xml',
        'wizard/message_wizard_views.xml',  # TAMBAHKAN INI
        'views/product_template_views.xml',
        'views/serial_number_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}