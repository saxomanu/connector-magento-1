# -*- coding: utf-8 -*-
# Copyright 2019 Callino
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, models, fields
from odoo.addons.component.core import Component
from odoo.addons.queue_job.job import job, related_action

_logger = logging.getLogger(__name__)



class MagentoProductProduct(models.Model):
    _inherit = 'magento.product.product'
    
    @api.depends('magento_attribute_line_ids')
    def _compute_custom_values_count(self):
        for product in self:
            product.custom_values_count = len(product.magento_attribute_line_ids)

    attribute_set_id = fields.Many2one('magento.product.attributes.set',
                                       string='Attribute set')
    
    magento_attribute_line_ids = fields.One2many(comodel_name='magento.custom.attribute.values',
                                                 inverse_name='magento_product_id', 
                                                 string='Magento Simple Custom Attributes Values',
                                        )
    custom_values_count = fields.Integer('Custom Values Count', compute='_compute_custom_values_count')

    
    @api.multi
    @job(default_channel='root.magento')
    def sync_to_magento(self):
        for binding in self:
            binding.with_delay().run_sync_to_magento()

    @api.multi
    @related_action(action='related_action_unwrap_binding')
    @job(default_channel='root.magento')
    def run_sync_to_magento(self):
        self.ensure_one()
        with self.backend_id.work_on(self._name) as work:
            exporter = work.component(usage='record.exporter')
            return exporter.run(self)

    @api.model
    def create(self, vals):
        mg_prod_id = super(MagentoProductProduct, self).create(vals)
        org_vals = vals.copy()
        attributes = mg_prod_id.attribute_set_id.attribute_ids.filtered(
            lambda x: x.odoo_field_name.id != False
            )
        cstm_att_mdl = self.env['magento.custom.attribute.values']
        if len(mg_prod_id.magento_attribute_line_ids) > 0:
            return mg_prod_id
        for att in attributes:
            vals = {
                #                 'backend_id': self.backend_id.id,
                'magento_product_id': mg_prod_id.id,
                'attribute_id': att.id,
                'store_view_id': False
                #                 'magento_attribute_type': att.frontend_input,
                #                 'product_template_id': self.odoo_id.id,
                #                 'odoo_field_name': att.odoo_field_name.id or False
            }
            cst_value = cstm_att_mdl.with_context(no_update=True).create(vals)
            #if cst_value.odoo_field_name.id:
            mg_prod_id.check_field_mapping(
                    cst_value.odoo_field_name.name,
                    mg_prod_id[cst_value.odoo_field_name.name])
                
#         if 'custom_attributes' in org_vals:
#             magento_attr_mdl = self.env['magento.product.attribute']            
#             for cst in org_vals['custom_attributes']:
#                 cst_value_id = mg_prod_id.magento_template_attribute_value_ids.filtered(
#                     lambda v: v.attribute_id.attribute_code == cst['attribute_code'])
#                 if cst_value_id.odoo_field_name.id:
#                     mg_prod_id.check_field_mapping(
#                         cst_value_id.odoo_field_name.name, 
#                         cst['value']
#                         )
#                 elif cst_value_id.id:
#                     cst_value_id.write({
#                         'attribute_text': cst['value']})
#             
#         if mg_prod_id.odoo_id.product_variant_count > 1 :
#             self.env['magento.template.attribute.line']._update_attribute_lines(mg_prod_id)
        
        return mg_prod_id
    

class ProductProductAdapter(Component):
    _inherit = 'magento.product.product.adapter'
    _magento2_name = 'product'

    def _get_id_from_create(self, result, data=None):
        # Products do use the sku as external_id - but we also need the id - so do return the complete data structure
        return result

#     def write(self, id, data, storeview_id=None):
#         """ Update records on the external system """
#         # XXX actually only ol_catalog_product.update works
#         # the PHP connector maybe breaks the catalog_product.update
#         if self.work.magento_api._location.version == '2.0':
#             _logger.info("Prepare to call api with %s " % data)
#             return super(ProductProductAdapter, self)._call(
#                 'products/%s' % data['sku'], {
#                     'product': data
#                 },
#                 http_method='put')
#         return self._call('ol_catalog_product.update',
#                           [int(id), data, storeview_id, 'id'])

    def put_image(self, id, data, storeview_id=None):
        """ Update records on the external system """
        if self.work.magento_api._location.version == '2.0':
            return super(ProductProductAdapter, self)._call(
                'products/%s/media' % id, {
                    "entry": {
                        "media_type": "image",
                        "label": "Image",
                        "position": 1,
                        "disabled": False,
                        "types": [
                            "image",
                            "small_image",
                            "thumbnail"
                        ],
                        "content": {
                            "base64EncodedData": data['image'],
                            "type": "image/png",
                            "name": data['filename']
                        }
                    }
                },
                http_method='post',
                storeview=storeview_id
            )
