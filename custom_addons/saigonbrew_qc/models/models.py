# -*- coding: utf-8 -*-

from odoo import models, fields, api

class ProductionQCModel(models.Model):
    _inherit = 'mrp.production'

    brewing_temp = fields.Float(string="Brewing Temperature",required=True)
    qc_passed_by = fields.Many2one('res.users', string="QC Passed By")