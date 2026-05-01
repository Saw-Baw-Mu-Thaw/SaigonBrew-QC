# -*- coding: utf-8 -*-
{
    'name': "saigonbrew_qc",

    'summary': """
        Adds quality control to manufacturing""",

    'description': """
        Adds 2 new fields to manufacturing order. Brewing temp and QC Passed By
    """,

    'author': "SaigonBrew",
    'website': "http://www.sgnbrew.com",

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/13.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Uncategorized',
    'version': '0.1',

    # any module necessary for this one to work correctly
    'depends': ['base','mrp'],

    # always loaded
    'data': [
        'security/ir.model.access.csv',
        'views/views.xml',
        'views/templates.xml',
    ],
    # only loaded in demonstration mode
    'demo': [
        'demo/demo.xml',
    ],
}
